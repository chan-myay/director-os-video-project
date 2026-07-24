# Director OS Storage Cleanup Audit

Status: read-only audit. Nothing has been removed.

## Must keep

### Approved face swappers

- `local-tools/facefusion/.assets/models/hififace_unofficial_256.onnx`
  — 194 MB
- `local-tools/facefusion/.assets/models/uniface_256.onnx`
  — 388 MB

### FaceFusion support models

Keep face detection, recognition, landmark, masking and safety dependencies,
including:

- `arcface_w600k_r50.onnx`
- `retinaface_10g.onnx`
- `2dfan4.onnx`
- `fan_68_5.onnx`
- `bisenet_resnet_34.onnx`
- `xseg_1.onnx`
- `fairface.onnx`
- `nsfw_1.onnx`, `nsfw_2.onnx`, `nsfw_3.onnx`
- `crossface_hififace.onnx`

### Current trained lead performer models

Do not remove:

- `face-correction/work/models/p03-performer-dlight-v1/`
- `face-correction/v2/models/p03-performer-dlight-384-v2/`

The current model files are approximately 1.5 GB and 2.0 GB respectively.

### Project truth and production

Do not remove:

- `audio/`
- `references/`
- `production/raw/`
- `production/selected/`
- `production/revised-singing-direction/`
- `director-os/projects/burmese-music-video/`
- corrected lyrics, prompts, storyboards, face sources and target clips

## Safest removable group — approximately 3.2 GB

These are caches/downloads or cloned research code and can be recreated:

| Folder | Size | Effect |
|---|---:|---|
| `local-tools/facefusion/.caches/` | 1.8 GB | Download/runtime cache; FaceFusion assets remain |
| `local-tools/conda-pkgs/` | 491 MB | Conda package download cache |
| `local-tools/pip-cache/` | 466 MB | Python package download cache |
| `local-tools/research-repos/` | 401 MB | Research clones; not the production pipeline |

This group does not include the approved face models, current environments,
lead performer references or production video.

## Unused FaceFusion swapper downloads — approximately 6 GB

The current approved final swappers are HiFiFace 256 and UniFace 256. The
following downloaded alternatives are not approved for the final workflow:

| File/group | Approximate size |
|---|---:|
| `blendswap_256.onnx` | 1.58 GB |
| `ghost_1_256.onnx`, `ghost_2_256.onnx`, `ghost_3_256.onnx` | 2.01 GB |
| `inswapper_128.onnx`, `inswapper_128_fp16.onnx` | 794 MB |
| `hyperswap_1a/1b/1c_256.onnx` | 1.15 GB |
| `simswap_256.onnx`, `simswap_unofficial_512.onnx` | 438 MB |

Location:

`local-tools/facefusion/.assets/models/`

These should be removed only by an explicit file allowlist. Do not remove the
entire models folder.

## Trained-model history — 10.76 GB, do not remove yet

This is the largest reclaimable-looking group, but it contains valuable
training history:

- DLight V1 snapshots from 1,000 through 10,000 iterations
- DLight V2 snapshots from 1,000 through 4,000 iterations
- two large `.bk` backup model files

Locations:

- `face-correction/work/models/p03-performer-dlight-v1_snapshot_*`
- `face-correction/v2/models/p03-performer-dlight-384-v2_snapshot_*`
- backup files ending in `.bk`

The current V1 and V2 model folders remain separate. Before removing snapshots,
archive their small state/metadata records and verify the current models open.

## Other large folders to keep for now

| Folder | Size | Reason |
|---|---:|---|
| `director-os/projects/` | 461 MB | Current project evidence and rescue outputs |
| `director-os/animatics/` | 161 MB | Previous full-song work |
| `director-os/listening-sync/` | 107 MB | Preserved Audio Truth evidence |
| `output/vocal-separation/` | 130 MB | Preserved audio evidence |
| `face-correction/model-bakeoff/` | 385 MB | Model comparison/failure memory |

## Recommended order if cleanup is approved

1. Safest cache/research group: approximately 3.2 GB.
2. Explicit unused-swapper file allowlist: approximately 6 GB.
3. Stop and verify free space and face pipeline.
4. Treat DLight snapshots as a separate archive operation, not routine cleanup.

