# Director OS v1.0.1 Local Storyboard Activation Report

Date: 2026-07-12

## Summary

Director OS now has a narrow, production-safe local storyboard model activation path:

- one recommended primary local backend
- one lightweight fallback
- no cloud option on the primary setup page
- approval records and install-plan packaging
- no model download before explicit install approval
- benchmark persistence
- storyboard-card variant persistence
- origin labeling for every generated or fallback image
- fake backend coverage for automated tests

The local AI storyboard backend is **not operational yet** because no real model install/download approval has been executed and no real image benchmark has passed.

## v0.1-v1.0 Preservation

Preserved:

- Run 9
- Run 11
- all existing MP4 animatics
- existing ready_with_approvals state
- existing production-control infrastructure
- existing composite previs
- existing storyboard/caption/animatic/QC/job/export/result systems

No source media was deleted, moved, overwritten, uploaded, or used in a cloud call.

## Detected Hardware

Verified cheap local facts:

- Architecture: arm64
- macOS: 15.6.1
- Python: 3.7.9
- Free disk: about 23 GiB
- Unified memory: 17,179,869,184 bytes from existing memory-pressure evidence, about 16 GiB

Existing toolchain state:

- FFmpeg: found at `local-tools/envs/faceswap/bin/ffmpeg`
- FFprobe: found at `local-tools/envs/faceswap/bin/ffprobe`
- MLX Python package: not installed
- Core ML tools: not installed
- Torch/MPS: not installed
- OpenCV: not installed
- PySceneDetect: not installed
- OpenTimelineIO: not installed
- Existing ComfyUI code: present

The Apple chip model is still not reliably captured by the local state because the previous `sysctl` probe was sandbox-limited.

## Selected Primary

Primary recommendation:

- Runtime: MFLUX on MLX/Metal
- Model path: Z-Image Turbo-class model through the MFLUX model registry
- Official source: https://github.com/filipstrand/mflux
- Pinned commit: `97ac5e6280e8c65e48a609722229eb9d03ef2cbe`
- Code license: MIT
- Model license: must be verified from the resolved model card before download
- Commercial-use state: `MODEL_LICENSE_REVIEW_REQUIRED`

Why selected:

- Native Apple-Silicon-oriented MLX path
- Local, private execution after install
- Maintained image-generation runtime
- Supports core storyboard tasks more directly than a broad ComfyUI stack for this first activation

Known limits:

- MLX is not installed yet
- Exact model file list and byte size must be resolved from the model card before download
- Identity/reference reliability is not guaranteed
- A real health benchmark and approved-project test frame are required before operational status

## Selected Lightweight Fallback

Fallback recommendation:

- Runtime: Apple Core ML Stable Diffusion
- Model path: Core ML converted Stable Diffusion 2.1 base 512px package
- Official source: https://github.com/apple/ml-stable-diffusion
- Pinned commit: `e12202c1f6405b83918b58a5d097cd61e3e1f702`
- Code license: MIT
- Model license: must be verified from the selected model card before download
- Commercial-use state: `MODEL_LICENSE_REVIEW_REQUIRED`

Why selected:

- Apple-maintained Core ML path
- Documented Apple-Silicon target runtime
- Safer 512px fallback scope for this Mac

Known limits:

- Core ML tools are not installed yet
- Model package size must be resolved before download
- Less capable than the primary path for cinematic prompt adherence
- No guaranteed identity/reference control

## Not Selected

ComfyUI was not selected for v1.0.1 activation because this patch must activate one narrow local engine, not multiple model stacks. ComfyUI remains a future/trusted-local-server option, without ComfyUI-Manager or unreviewed custom nodes.

DiffusionKit was not selected for this activation because the available quick audit did not provide enough current implementation detail to prefer it over MFLUX or Apple Core ML Stable Diffusion for the first narrow benchmark path.

## Setup Page

Updated:

- `/setup/storyboard-model`

The page now shows only:

- recommended primary
- lightweight fallback
- continue with composite previs
- decide later

Removed from the main setup page:

- generic cloud option
- generic broad ComfyUI recommendation

Buttons now record:

- `Approve primary`
- `Approve lightweight fallback`
- `Continue with composite previs`
- `Decide later`

Recording an approval creates an install-plan package only. It does not download model files or run installer commands.

## Database Additions

Added tables:

- `storyboard_model_installations`
- `storyboard_model_benchmarks`
- `storyboard_ai_variants`

Development database state after migration:

- storyboard model installations: 0
- storyboard model benchmarks: 0
- storyboard AI variants: 0

This is correct because no real production model approval or benchmark has been executed.

## Install Package Behavior

After approval, Director OS writes an install-plan package under the configured storyboard-model root.

Package files:

- `INSTALL_PLAN.md`
- `COMMANDS.json`
- `APPROVAL_STATUS.json`
- `UNINSTALL.md`

Commands are stored as argument arrays, not shell-interpolated strings.

No installer route currently downloads model files automatically. A later explicit install action must execute only the approved package.

## Exact Files Downloaded

None.

No model weights, model files, repositories, pip packages, custom nodes, or cloud assets were downloaded during this patch.

## Benchmarks

Real benchmark status:

- Non-private health test: not run against a real model
- Approved-project test: not run against a real model
- Operational backend: false

Automated test benchmark:

- Uses fake backend only
- Writes isolated output under `director-os-web/test-output/`
- Origin label: `PLACEHOLDER`
- Does not count as a project AI frame
- No upload
- No API call
- No model download

## Real Local AI Project-Frame Count

Real local AI project frames: 0

Composite previs frames in current development database: 288 records across existing sync/run history, with 24 active storyboard cards.

## Origin Labeling

Supported labels:

- `LOCAL AI GENERATED PREVIS`
- `LOCAL ASSET COMPOSITE PREVIS`
- `EXISTING SOURCE FRAME`
- `REFERENCE ONLY`
- `DIAGRAM`
- `PLACEHOLDER`

The fake test backend is labeled `PLACEHOLDER`, not `LOCAL AI GENERATED PREVIS`.

## Storyboard Integration

Added route:

- `POST /storyboard/{shot_number}/generate-local-ai`

Behavior now:

- If no operational model exists, route blocks with `LOCAL_STORYBOARD_MODEL_REQUIRED`
- If an operational model is later benchmarked, the route can create one-shot variants
- Version metadata is recorded per card
- Refinement text applies to one shot only
- Variant metadata records backend, origin label, prompt, refinement, seed, size, and safety flags

The smoke test verified the requested refinement text against one card using a fake backend only:

> Move the performer toward the right third, retain cold negative space near the winter window, remove background people, keep arms below shoulder height, and strengthen the warm practical lighting.

## Test Isolation

Updated smoke-test output roots:

- `DIRECTOR_OS_STORYBOARD_MODEL_ROOT=director-os-web/test-output/storyboard-model`
- `DIRECTOR_OS_STORYBOARD_VARIANT_ROOT=director-os-web/test-output/storyboard-variants`

The smoke test uses:

- isolated test database
- isolated result-media folder
- isolated storyboard-model test folder
- isolated storyboard-variant test folder
- mock intelligence provider
- fake model backend

No normal development database records are created by the smoke test.

## Temporary Non-Operational Files

During the first smoke-test pass before test-output isolation was tightened, non-operational test files were written under:

- `director-os/local-generation/storyboard-model/primary/`
- `director-os/storyboard-ai-variants/`

They contain no model weights, no downloaded packages, no private copied media, and no production database records. They are not counted as operational or as real local AI frames.

## Validation

Passed:

```bash
python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)
```

Passed:

```bash
cd director-os-web
python3 scripts/smoke_test_local.py
```

Smoke test confirmed:

- no download before approval
- exact approved model path is recorded as an install plan only
- install commands are argument arrays
- fake benchmark output is not labeled as AI generation
- real generation route blocks without an operational model
- one-shot fake variant affects only one storyboard card
- no API/upload/generation occurs
- development database counts remain unchanged during smoke test

## Approval Status

No real production model-install approval has been recorded.

No model install has been executed.

No benchmark has passed.

Local storyboard backend remains:

`local_after_install`

not:

`operational`

## Uninstall Instructions

If a future approved install is executed:

- Primary path: remove `director-os/local-generation/storyboard-model/primary`
- Fallback path: remove `director-os/local-generation/storyboard-model/fallback`
- Clear related installation and benchmark records if the user explicitly wants the backend forgotten
- Do not touch source media, Run 9, Run 11, animatics, or composite previs

For test-only output:

- `director-os-web/test-output/` is regenerated by smoke tests and contains no private source media.

## Limitations

- MLX is not installed yet
- Core ML tools are not installed yet
- No model files were downloaded
- No real AI image was generated
- No quality review has been performed on a real AI frame
- Model license and exact download file list still require final model-card resolution before installation
- Free disk is tight for large image/video models, around 23 GiB available

## Next Action

Open:

`/setup/storyboard-model`

Then choose one:

1. Approve primary local installation
2. Approve lightweight fallback
3. Continue with composite previs
4. Decide later

The next production action is to approve one storyboard backend install, then run the non-private health benchmark before attempting one approved-project storyboard frame.
