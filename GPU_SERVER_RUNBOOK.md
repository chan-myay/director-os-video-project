# GPU Server Continuation Runbook

## Scope

A private GPU server can accelerate face correction, local lip-sync experiments,
and supported generation. It does not repair incorrect lyric timing by itself.
Human review and invalidated Audio Truth anchors must survive any move.

## What is intentionally not in Git

- master song, WAV stems, generated clips, and animatics;
- private A1/A2/B references;
- ASR, InfiniteTalk, FaceFusion, or trained performer model weights;
- environments, caches, decoded frames, and API credentials.

Transfer private assets through an encrypted channel or redownload public models
from their documented sources. Never add credentials or performer media to Git.

## Baseline

Use a private Linux NVIDIA host with a compatible driver/CUDA/PyTorch set,
`nvidia-smi`, FFmpeg, FFprobe, Git, Python, sufficient temporary storage, and
isolated environments. Do not guess version compatibility. Reconstruct it from
the retained package locks and chosen upstream revision, then record resolved
versions and model hashes in a new run manifest.

Preserve this logical layout:

```text
project-root/
  director-os-web/
  director-os/
  face-correction/
  local-models/
  local-tools/
  audio/
  lyrics/
  references/
  production/
```

Historical `/Users/chan/song-video-project/...` paths are provenance, not
portable configuration. New execution should resolve one project root without
rewriting historical evidence.

## Audio Truth on GPU

Preserved facts:

- master duration is approximately 292.702 seconds;
- the canonical lyric source is manually corrected Unicode;
- Demucs separation completed;
- Burmese CTC and Whisper passed technical health but recognition was imperfect;
- v3 produced a monotonic 21-occurrence path;
- real review invalidated part of the v3 anchor assumption;
- v4 retains one verified early anchor, two replacement candidates, 9 ready
  occurrences, and 12 blocked occurrences.

Continuation rules:

1. Verify master and lyric SHA-256 hashes.
2. Restore/redownload models recorded in v2 status and the package lock.
3. Validate model hashes and licenses.
4. Write a new versioned result; never overwrite v4.
5. Compare all boundaries against the verified early anchor.
6. Keep real-review-invalidated occurrences blocked.
7. Require review before promoting the middle/late replacement anchors.

The visual edit remains unblocked while alignment research continues.

## Lip-sync on GPU

Provider modes already represented in code:

- `manual_infinitetalk`: manual job package.
- `local_infinitetalk`: code detection, non-operational until a benchmark passes.
- `runpod_infinitetalk`: configuration health only; submission remains disabled.

Recognized RunPod environment names:

```text
RUNPOD_API_KEY
RUNPOD_INFINITETALK_ENDPOINT_ID
RUNPOD_INFINITETALK_BASE_URL
RUNPOD_MAX_COST_USD
RUNPOD_MAX_RUNTIME_MINUTES
```

Do not commit their values. Current code does not submit jobs automatically.

First proof:

1. Select one accepted, face-stable performer clip.
2. Select one v4-ready occurrence, never blocked or invalidated.
3. Build the exact vocal/full-mix segment on the master timebase.
4. Render only a short proof.
5. Check identity, eyes, teeth/tongue, jaw edge, timing, frame continuity, audio
   duration, and input/output hashes.
6. Reject plausible-looking mouth motion that is not tied to verified audio.
7. Preserve manifest, provider revision, settings, logs, output, and QC decision.

Do not batch the full song until a short proof passes.

## Face correction on GPU

The retained approved comparison is HiFiFace 256 versus UniFace 256.

1. Transfer accepted clip and identity source privately; verify hashes.
2. Recreate FaceFusion at a recorded revision.
3. Benchmark both models on the same short segment with identical crop, detector,
   mask, and output settings.
4. Review temporal identity, texture, lighting, occlusion, mouth, and anatomy.
5. Select per clip rather than declaring one global winner.
6. Preserve untouched source and both comparison outputs.

DLight state JSON does not replace matching weights and training data. Never
resume from metadata alone.

## Generation and edit

Gemini/Flow, Veo, Kling, Seedance, Runway, generic image, and generic
image-to-video prompts are preserved. Generation remains manual export/import
unless a connector is explicitly approved and operational.

The bar is an anchor, not the whole visual world. Winter nature, Finnish
exteriors, Burmese art/architecture, memory, symbolic inserts, band/audience
life, and tasteful adult background movement are available. The lead performance
remains mature and singing-led.

## Every expensive run

Before:

- resolve exact input/output paths;
- record hashes, model/provider revision, cost limit, and runtime limit;
- confirm private handling and a new non-destructive output directory;
- define the short proof and QC/rollback plan.

After:

- probe duration, resolution, aspect ratio, codecs, and playability;
- visually review identity and motion;
- classify usable, usable with trim, reference only, wrong shot, corrupted, or
  rejected;
- import only accepted assets;
- rebuild in the background;
- verify the full-song clean result has no cutoff.

