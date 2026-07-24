# Local-First Stack Decision

## Decision

Director OS v1.0 keeps local deterministic tooling as the operational baseline:

- SQLite for state
- FFmpeg/FFprobe for media generation and validation
- local PNG composite previs as fallback
- local caption processing
- local project archaeology
- local result/QC/audit pipeline

## Adopt

- FFmpeg/FFprobe: already operational and benchmarked locally.
- SQLite: already operational.
- OpenTimelineIO-style exports: current OTIO placeholder exists; production adapter remains incremental.
- Local composite previs: useful fallback, always labeled `LOCAL ASSET COMPOSITE PREVIS`.

## Adapt

- MLX / MLX-LM: promising Apple Silicon local intelligence path. Verified upstream HEAD `4367c73b60541ddd5a266ce4644fd93d20223b6e`. Not installed as a Director OS model runtime in this build.
- llama.cpp: promising local/edge LLM server path. Verified upstream HEAD `e3546c7948e3af463d0b401e6421d5a4c2faf565`. Not configured in this build.
- SoeMind Forge: verified user repo HEAD `42e055367d12346e27cb4aa1470b3d3a2bbf8d37`. Use as inspiration for one-command media workflow, caption/voice orchestration and preview-before-spend; do not copy blindly.

## Defer

- Local final video generation on this Mac: likely experimental or slow until a specific model/runtime is approved and benchmarked.
- InfiniteTalk local: defer until official source/model/license/GPU requirements are verified. Current classification: `local_after_install` / not operational.
- Burmese local TTS: defer until a real Burmese-capable local provider produces a benchmarked WAV.

## Reject For Now

- Unreviewed ComfyUI custom nodes.
- Any repository that requires automatic model-weight downloads during install.
- Any paid/cloud execution without explicit upload and spend approval.

## Evidence

- VideoAgent paper/repo indicates a multi-agent video editing architecture and code at `https://github.com/HKUDS/VideoAgent`; HEAD verified as `44611659e43628c5eb7f77158b3b94a32bcbb5c5`.
- Zawgyi/Unicode remains a real Burmese interoperability issue; Director OS preserves original text and treats conversion uncertainty explicitly.
- InfiniteTalk paper describes sparse-frame audio-driven video dubbing, but no local model/runtime was installed or benchmarked in this build.
