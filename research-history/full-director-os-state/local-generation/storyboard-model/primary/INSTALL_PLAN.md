# Storyboard Model Install Plan

Status: APPROVAL RECORDED ONLY

No command in this plan has been executed by Director OS.
No model file has been downloaded.

## Selected Backend
MFLUX local MLX image backend with Z-Image Turbo-class model

## Runtime
MFLUX on MLX/Metal

## Model
Z-Image Turbo through MFLUX model registry

## Official Source
https://github.com/filipstrand/mflux

## Pinned Commit
97ac5e6280e8c65e48a609722229eb9d03ef2cbe

## License
MFLUX code: MIT. Model license must be verified from the resolved model card before download.

## Commercial Use
MODEL_LICENSE_REVIEW_REQUIRED before production use.

## Exact Files
- MFLUX source at commit 97ac5e6280e8c65e48a609722229eb9d03ef2cbe
- Hugging Face model files resolved by MFLUX for Z-Image Turbo after approval
- pip wheels recorded in isolated venv after approval

## Commands
Commands are stored as argument arrays and must be executed only after explicit install confirmation.

- `["python3", "-m", "venv", "director-os/local-generation/storyboard-model/primary/.venv"]`
- `["director-os/local-generation/storyboard-model/primary/.venv/bin/python", "-m", "pip", "install", "--upgrade", "pip"]`
- `["director-os/local-generation/storyboard-model/primary/.venv/bin/python", "-m", "pip", "install", "git+https://github.com/filipstrand/mflux.git@97ac5e6280e8c65e48a609722229eb9d03ef2cbe"]`
- `["director-os/local-generation/storyboard-model/primary/.venv/bin/python", "-m", "mflux", "--help"]`

## Uninstall
Remove director-os/local-generation/storyboard-model/primary and clear the related installation record; no source media is touched.
