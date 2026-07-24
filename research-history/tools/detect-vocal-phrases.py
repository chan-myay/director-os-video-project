#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "output/vocal-separation/vocals-analysis.wav"
OUTPUT = ROOT / "output/lyric-alignment/vocal-phrase-boundaries.json"

sample_rate, audio = wavfile.read(INPUT)
audio = audio.astype(np.float32) / 32768.0

hop_seconds = 0.02
window_seconds = 0.10
hop = int(sample_rate * hop_seconds)
window = int(sample_rate * window_seconds)

rms = []
for start in range(0, len(audio) - window + 1, hop):
    frame = audio[start:start + window]
    rms.append(float(np.sqrt(np.mean(frame * frame) + 1e-12)))
rms = np.asarray(rms)

floor = float(np.percentile(rms, 20))
ceiling = float(np.percentile(rms, 90))
threshold = floor + 0.22 * (ceiling - floor)
active = rms >= threshold

# Fill short internal gaps so consonants and breaths remain within one phrase.
max_gap = int(0.12 / hop_seconds)
indices = np.flatnonzero(active)
for left, right in zip(indices[:-1], indices[1:]):
    if 1 < right - left <= max_gap:
        active[left:right + 1] = True

# Remove very short activations.
minimum_phrase = int(0.35 / hop_seconds)
regions = []
start = None
for index, value in enumerate(np.r_[active, False]):
    if value and start is None:
        start = index
    elif not value and start is not None:
        if index - start >= minimum_phrase:
            regions.append([start * hop_seconds, index * hop_seconds + window_seconds])
        start = None

# Merge only tiny dropouts; retain breaths and lyric-line endings.
merged = []
for start, end in regions:
    if merged and start - merged[-1][1] < 0.18:
        merged[-1][1] = end
    else:
        merged.append([start, end])

payload = {
    "source": str(INPUT.relative_to(ROOT)),
    "sample_rate": sample_rate,
    "hop_seconds": hop_seconds,
    "threshold": threshold,
    "noise_floor": floor,
    "high_energy_reference": ceiling,
    "phrases": [
        {"index": index + 1, "start": round(start, 2), "end": round(end, 2),
         "duration": round(end - start, 2)}
        for index, (start, end) in enumerate(merged)
    ],
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

print(f"Detected {len(merged)} vocal regions")
for phrase in payload["phrases"]:
    print(f'{phrase["index"]:02d}  {phrase["start"]:7.2f} - '
          f'{phrase["end"]:7.2f}  ({phrase["duration"]:5.2f}s)')
