# Director OS — Private Burmese Creator (CPU-first pilot)

This is a **working, bounded first stage**, not a claim of a complete AI film studio. It takes Burmese text and an optional supplied image, synthesizes local Nara Mini v1 speech (`ko-banyar` default), uses actual WAV segment durations for **sentence-level** SRT captions, burns those captions with FFmpeg/libass, animates the still with a subtle diagonal camera move, and exports `narration.mp3`, `captions.srt`, and `video.mp4`.

## Truth about the limitations

- **Voice**: requires a separately installed Nara Mini v1 ONNX model and its dependencies, at `NARA_MINI_ROOT`. The public GitHub repo must not contain private reference recordings or scripts. Use the publisher's `synthesize.py`; the model is not shipped here.
- **Subtitles**: sentence-timed by actual synthesized segment length. No word-by-word karaoke/lyric highlighting or forced alignment is claimed. The old lyric/Audio Truth materials stay preserved for later verified adapters.
- **Image**: accepts your existing image; if none supplied, creates a graphic placeholder. A cheap pan/crop does **not** constitute animated character/dance video or text-to-image AI. Those remain future optional local-backend integrations.
- **Rendering**: no cloud generation, user account or public upload. CPU and disk requirements need testing on the real VPS. One render job is processed at a time; progress survives on disk but an interrupted job needs resubmission/recovery.
- **Existing full Director OS**: preserve the music-video work. On a public VPS run only the isolated `app.creator_server:app`. **Do not expose `app.main` publicly:** legacy routes mount the working project and private reference folders.

## Install once (Mac/Linux, from `director-os-web`)

Python 3.10+, FFmpeg with `libass` and `libmp3lame`, an installed Noto Sans Myanmar font, and the Nara Mini v1 code + Ko Banyar ONNX files are required. On Debian/Ubuntu, `ffmpeg`, `fonts-noto-core`, Python `venv`, and Python's dependencies are usually enough for the video layer. Nara's own `requirements.txt` installs the speech dependencies. No GPU is required for the ONNX example but **speed is not guaranteed** on a small CPU VPS.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
# Set this to a private directory containing the official synthesize.py and model weights.
export NARA_MINI_ROOT="$HOME/private-models/nara-mini-v1"
export CREATOR_OUTPUT_ROOT="$HOME/private-director-renders"
export CREATOR_USERNAME='creator'
export CREATOR_PASSWORD='set-a-long-unique-random-password'
./scripts/run_creator_vps.sh
```

Go to `http://127.0.0.1:8788/creator/` on your own machine. When running on a VPS, place it behind an authenticated TLS reverse proxy and bind the app **only to 127.0.0.1**. Keep the private model and media directories outside the Git repo/web root and protect server backups.

### One-command CLI (no browser)

```bash
. .venv/bin/activate
python scripts/creator_cli.py --text-file /path/to/story.txt --image /path/to/illustration.jpg --voice ko-banyar
```

The CLI prints absolute MP3, MP4 and SRT paths. The UI shows a player and downloads under `Create → Burmese Creator`. Do not put private sample scripts, voice recordings or image assets in Git.

### Operational validation

```bash
python -m pytest -q tests/test_creator_engine.py
ffmpeg -filters | grep -E ' subtitles | ass '
```

The automated test uses a **fake TTS renderer**, not the Nara voice. Acceptance on your VPS additionally requires a real Ko Banyar paragraph with a Burmese name and number, audio listening, actual video playback, script/number checks, Myanmar glyph shaping checks, memory/latency measurements, and an unauthenticated-access denial test.

**Nara attribution:** Nara Mini v1 by Nara contributors, https://naraaudio.app and https://huggingface.co/YeeNyunn/nara-mini-v1; Apache-2.0; preserve the model's LICENSE and NOTICE when redistributing it.