"""CPU-first, private Burmese narrated-video renderer for Director OS.

No external API calls or model downloads happen here. The approved Nara Mini
model must already exist at NARA_MINI_ROOT. Intermediate media and input text
stay under the private CREATOR_OUTPUT_ROOT.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from uuid import uuid4


MAX_TEXT = 5000
DEFAULT_VOICE = "ko-banyar"
SUPPORTED_VOICES = ("ko-banyar", "shoon", "thazin", "htet-myat")


def output_root() -> Path:
    return Path(os.environ.get("CREATOR_OUTPUT_ROOT", str(Path.home() / ".director-os" / "private-creator"))).expanduser().resolve()


def safe_job_id(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{32}", value):
        raise ValueError("Invalid job identifier")
    return value


def job_dir(job_id: str) -> Path:
    return output_root() / safe_job_id(job_id)


def new_job(text: str, voice: str = DEFAULT_VOICE, *, visual: bytes | None = None, visual_name: str = "") -> str:
    text = text.strip()
    if not text or len(text) > MAX_TEXT:
        raise ValueError(f"Text must be between 1 and {MAX_TEXT} characters")
    if voice not in SUPPORTED_VOICES:
        raise ValueError("Unsupported voice")
    root = output_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    job_id = uuid4().hex
    folder = job_dir(job_id)
    folder.mkdir(mode=0o700)
    (folder / "input.txt").write_text(text, encoding="utf-8")
    (folder / "input.txt").chmod(0o600)
    visual_ext = ""
    if visual:
        if len(visual) > 25 * 1024 * 1024:
            raise ValueError("Visual file must be at most 25 MB")
        visual_ext = validate_and_store_visual(folder, visual, visual_name)
    write_status(job_id, "queued", voice=voice, visual_ext=visual_ext)
    return job_id


def validate_and_store_visual(folder: Path, content: bytes, filename: str) -> str:
    # Filenames from browsers are never used as output paths.
    ext = Path(filename).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Upload a PNG, JPEG or WebP still image")
    try:
        from PIL import Image, ImageOps
        from io import BytesIO
        with Image.open(BytesIO(content)) as im:
            im.verify()
        with Image.open(BytesIO(content)) as im:
            im = ImageOps.exif_transpose(im)
            if im.width * im.height > 25_000_000:
                raise ValueError("Image dimensions are too large")
            im.convert("RGB").save(folder / "visual.jpg", format="JPEG", quality=91)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Invalid image file") from exc
    (folder / "visual.jpg").chmod(0o600)
    return ".jpg"


def write_status(job_id: str, state: str, **extra: object) -> None:
    folder = job_dir(job_id)
    old = {}
    f = folder / "status.json"
    if f.is_file():
        old = json.loads(f.read_text(encoding="utf-8"))
    payload = {**old, "id": job_id, "status": state, **extra}
    temp = folder / "status.tmp"
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(f)
    f.chmod(0o600)


def read_status(job_id: str) -> dict:
    f = job_dir(job_id) / "status.json"
    if not f.is_file():
        raise FileNotFoundError(job_id)
    return json.loads(f.read_text(encoding="utf-8"))


def segments(text: str) -> list[str]:
    # Sentence-level timing avoids pretending to have word-level forced alignment.
    text = text.strip()
    pieces = re.split(r"(?<=[။!?။!?])\s*|(?<=။)", text)
    pieces = [p.strip() for p in pieces if p.strip()]
    # Chunk overly long paragraphs at whitespace, keeping exact text order.
    out: list[str] = []
    for piece in pieces:
        if len(piece) <= 240:
            out.append(piece)
            continue
        words = piece.split(" ")
        buf = ""
        for word in words:
            if buf and len(buf) + len(word) + 1 > 240:
                out.append(buf)
                buf = word
            else:
                buf = f"{buf} {word}" if buf else word
        if buf:
            out.append(buf)
    return out or [text]


def exec_checked(args: list[str], *, cwd: Path | None = None, timeout: int = 300) -> None:
    if not args or not shutil.which(args[0]) and not Path(args[0]).exists():
        raise RuntimeError(f"Missing executable: {args[0]}")
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        # Don't leak full private source or installed path in UI errors.
        raise RuntimeError(f"Renderer failed ({Path(args[0]).name}, exit {result.returncode})")


def synthesize_segments(folder: Path, text: str, voice: str) -> list[tuple[str, float]]:
    root_str = os.environ.get("NARA_MINI_ROOT", "")
    if not root_str:
        raise RuntimeError("NARA_MINI_ROOT must point to a local Nara Mini v1 installation")
    root = Path(root_str).expanduser().resolve()
    synth = root / "synthesize.py"
    if not synth.is_file():
        raise RuntimeError("Nara Mini synthesize.py is not installed")
    phrase_timings = []
    wavparams = None
    audio_frames: list[bytes] = []
    for i, phrase in enumerate(segments(text)):
        piece = folder / f"piece_{i:03d}.wav"
        exec_checked([sys.executable, str(synth), "--voice", voice, "--text", phrase, "--output", str(piece), "--threads", os.environ.get("CREATOR_CPU_THREADS", "2")], cwd=root, timeout=int(os.environ.get("CREATOR_TTS_TIMEOUT", "300")))
        if not piece.is_file():
            raise RuntimeError("Nara returned no WAV")
        with wave.open(str(piece), "rb") as audio:
            p = (audio.getnchannels(), audio.getsampwidth(), audio.getframerate())
            if p != (1, 2, 24000):
                raise RuntimeError("Nara output must be 24 kHz mono PCM16")
            if wavparams is not None and p != wavparams:
                raise RuntimeError("Incompatible WAV segments")
            wavparams = p
            frames = audio.readframes(audio.getnframes())
            secs = audio.getnframes() / audio.getframerate()
            if secs <= 0:
                raise RuntimeError("Empty WAV segment")
            phrase_timings.append((phrase, secs))
            audio_frames.append(frames)
    master = folder / "narration.wav"
    with wave.open(str(master), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(24000)
        for chunk in audio_frames:
            out.writeframes(chunk)
    master.chmod(0o600)
    return phrase_timings


def srt_time(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    hh, rest = divmod(ms, 3_600_000)
    mm, rest = divmod(rest, 60_000)
    ss, msec = divmod(rest, 1000)
    return f"{hh:02}:{mm:02}:{ss:02},{msec:03}"


def write_subtitles(folder: Path, timings: list[tuple[str, float]]) -> float:
    lines = []
    start = 0.0
    for i, (phrase, seconds) in enumerate(timings, 1):
        end = start + seconds
        lines.extend([str(i), f"{srt_time(start)} --> {srt_time(end)}", phrase, ""])
        start = end
    (folder / "captions.srt").write_text("\n".join(lines), encoding="utf-8")
    return start


def placeholder_visual(folder: Path) -> None:
    # Fallback is an honestly labeled graphic background, NOT an AI-generated scene.
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError("Install Pillow or provide a reference image") from exc
    im = Image.new("RGB", (720, 1280), (18, 24, 42))
    painter = ImageDraw.Draw(im)
    for i in range(70):
        y = 100 + i * 18
        painter.line((0, y, 720, y - 180), fill=(20 + (i % 6), 29 + (i % 14), 54 + (i % 21)), width=7)
    painter.ellipse((110, 200, 610, 700), outline=(78, 100, 125), width=7)
    im.save(folder / "visual.jpg", "JPEG", quality=93)
    (folder / "visual.jpg").chmod(0o600)


def render_video(folder: Path, duration: float) -> None:
    image = folder / "visual.jpg"
    if not image.exists():
        placeholder_visual(folder)
    # Force scale/crop to vertical; slow diagonal drift is CPU-cheap and deterministic.
    # Burn subtitles from SRT via libass; font selection is provided by the host OS.
    filter_expr = (
        "scale=780:1387:force_original_aspect_ratio=increase,"
        "crop=720:1280:x='(in_w-out_w)*(0.50+0.15*sin(n/105))':"
        "y='(in_h-out_h)*(0.50+0.12*cos(n/119))',"
        "fps=24,subtitles=captions.srt:charenc=UTF-8:force_style='Fontname=Noto Sans Myanmar,Fontsize=30,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,Outline=2,Shadow=0,"
        "MarginV=80,Alignment=2',format=yuv420p"
    )
    exec_checked([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "24",
        "-i", "visual.jpg", "-i", "narration.wav", "-filter_complex", f"[0:v]{filter_expr}[v]",
        "-map", "[v]", "-map", "1:a:0", "-t", f"{duration:.3f}", "-c:v", "libx264",
        "-threads", os.environ.get("CREATOR_CPU_THREADS", "2"), "-preset", "veryfast", "-crf", "24",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "video.mp4",
    ], cwd=folder, timeout=int(os.environ.get("CREATOR_VIDEO_TIMEOUT", "900")))
    exec_checked(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", "narration.wav", "-codec:a", "libmp3lame", "-qscale:a", "3", "narration.mp3"], cwd=folder)


def render_job(job_id: str) -> None:
    status = read_status(job_id)
    folder = job_dir(job_id)
    write_status(job_id, "running")
    try:
        text = (folder / "input.txt").read_text(encoding="utf-8")
        timings = synthesize_segments(folder, text, status["voice"])
        seconds = write_subtitles(folder, timings)
        render_video(folder, seconds)
        files = ["narration.mp3", "video.mp4", "captions.srt"]
        if not all((folder / f).is_file() and (folder / f).stat().st_size > 0 for f in files):
            raise RuntimeError("One or more outputs were empty")
        write_status(job_id, "complete", duration_seconds=round(seconds, 3), files=files, subtitle_level="sentence")
    except Exception as exc:
        write_status(job_id, "failed", error=str(exc)[:200])
        raise