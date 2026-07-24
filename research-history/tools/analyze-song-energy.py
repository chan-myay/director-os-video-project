#!/usr/bin/env python3
import json
import math
import wave
from pathlib import Path

import numpy as np

ROOT = Path("/Users/chan/song-video-project")
WAV = ROOT / "production/edit/roughcut-v2/song-analysis/master-mono-22050.wav"
OUTDIR = ROOT / "production/edit/roughcut-v2/song-analysis"
PHRASES = ROOT / "output/lyric-alignment/vocal-phrase-boundaries.json"


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return sr, x


def moving_average(x, n):
    if n <= 1:
        return x
    return np.convolve(x, np.ones(n) / n, mode="same")


def sec_to_mmss(t):
    m = int(t // 60)
    s = t - 60 * m
    return f"{m:02d}:{s:05.2f}"


sr, x = read_wav(WAV)
duration = len(x) / sr

# RMS energy at 100 ms hop
win = int(sr * 0.10)
hop = int(sr * 0.05)
rms = []
times = []
for i in range(0, len(x) - win, hop):
    frame = x[i : i + win]
    rms.append(float(np.sqrt(np.mean(frame * frame) + 1e-12)))
    times.append((i + win / 2) / sr)
rms = np.array(rms)
times = np.array(times)
rms_s = moving_average(rms, 7)

# Onset-ish novelty from positive RMS derivative
diff = np.maximum(0, np.diff(rms_s, prepend=rms_s[0]))
nov = moving_average(diff, 5)
thr = np.percentile(nov, 85)
peaks = []
last = -999
for i in range(1, len(nov) - 1):
    if nov[i] > thr and nov[i] >= nov[i - 1] and nov[i] >= nov[i + 1]:
        t = times[i]
        if t - last >= 0.28:
            peaks.append(t)
            last = t

# Estimate beat spacing from onset intervals between 0.35 and 1.2s
intervals = []
for a, b in zip(peaks, peaks[1:]):
    d = b - a
    if 0.35 <= d <= 1.20:
        intervals.append(d)
if intervals:
    med = float(np.median(intervals))
    bpm = 60.0 / med
else:
    med = None
    bpm = None

sections = [
    ("intro", 0.00, 32.18),
    ("verse1", 32.18, 92.58),
    ("chorus1", 97.66, 164.12),
    ("instrumental_breath", 164.12, 176.24),
    ("later_verse", 176.24, 234.58),
    ("chorus2_final", 235.44, 278.22),
    ("outro", 278.22, 292.66),
]

rows = []
global_mean = float(np.mean(rms_s))
global_p90 = float(np.percentile(rms_s, 90))
for name, a, b in sections:
    mask = (times >= a) & (times < b)
    if not np.any(mask):
        continue
    e = rms_s[mask]
    local_peaks = [p for p in peaks if a <= p < b]
    density = len(local_peaks) / max(1e-6, (b - a))
    mean = float(np.mean(e))
    p90 = float(np.percentile(e, 90))
    if p90 >= global_p90 * 0.98 or density > 1.25:
        movement = "HIGH: dance/body rhythm, sharper cuts"
    elif mean >= global_mean * 0.95:
        movement = "MEDIUM: walking, torso/arm phrases, controlled tension"
    else:
        movement = "LOW: setup, gaze, object cuts, held poses"
    rows.append(
        {
            "section": name,
            "start": a,
            "end": b,
            "mean_rms": mean,
            "p90_rms": p90,
            "onset_density_per_sec": density,
            "movement_directive": movement,
            "strong_onsets": [round(p, 2) for p in local_peaks[:24]],
        }
    )

report = []
report.append("# Song Energy / Movement Analysis")
report.append("")
report.append(f"Source: `audio/01.mp3`")
report.append(f"Duration: `{duration:.3f}` seconds")
if bpm:
    report.append(f"Approximate pulse estimate: `{bpm:.1f} BPM` from median onset spacing `{med:.3f}s`")
else:
    report.append("Approximate pulse estimate: unavailable")
report.append("")
report.append("## Section movement directives")
report.append("")
report.append("| Section | Time | Energy | Onsets/sec | Movement directive |")
report.append("|---|---:|---:|---:|---|")
for r in rows:
    report.append(
        f"| {r['section']} | `{sec_to_mmss(r['start'])}–{sec_to_mmss(r['end'])}` | "
        f"{r['p90_rms']:.3f} | {r['onset_density_per_sec']:.2f} | {r['movement_directive']} |"
    )
report.append("")
report.append("## Practical visual rules from the actual audio")
report.append("")
report.append("- The video cannot be a slow warm lounge slideshow; the waveform stays dense for most of the track.")
report.append("- Choreography must be generated as rhythm-driven dance phrases, especially in chorus and later verse sections.")
report.append("- Use held emotional close-ups only as punctuation, not as the main body of the music video.")
report.append("- Avoid fake singing-mouth close-ups until lip-sync is actually solved.")
report.append("- Batch D should prioritize full-body / knees-up movement with bar shelves and dark stage atmosphere.")
report.append("- The microphone should be symbolic only, not the visual center.")
report.append("")
report.append("## Strong onset examples by section")
report.append("")
for r in rows:
    report.append(f"### {r['section']} `{sec_to_mmss(r['start'])}–{sec_to_mmss(r['end'])}`")
    report.append("")
    report.append(", ".join(sec_to_mmss(p) for p in r["strong_onsets"]) or "(none)")
    report.append("")

(OUTDIR / "song-energy-analysis.json").write_text(json.dumps({"bpm": bpm, "sections": rows}, indent=2), encoding="utf-8")
(OUTDIR / "SONG-ENERGY-MOVEMENT-DIRECTIVES.md").write_text("\n".join(report), encoding="utf-8")
print("\n".join(report[:30]))
