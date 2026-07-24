# GitHub Architecture Audit

Source was shallow-cloned where reachable. No install scripts were run and no model weights were downloaded.

## SoeMind Forge

- Available locally: True
- Path: `local-tools/research-repos/soemind-forge`
- License first line: MIT License
- File count: 239
- Has package.json: True
- Has requirements.txt: False
- Has install/download scripts: True
- Decision: Learn workflow templates, cost tracking, captions/text overlay ideas; do not adopt Gemini-specific execution.

## HKUDS VideoAgent

- Available locally: True
- Path: `local-tools/research-repos/HKUDS-VideoAgent`
- License first line: MIT License
- File count: 878
- Has package.json: False
- Has requirements.txt: True
- Has install/download scripts: True
- Decision: Learn multi-agent orchestration and memory structure; do not adopt claims or API-heavy execution directly.

## FireRed-OpenStoryline

- Available locally: True
- Path: `local-tools/research-repos/FireRed-OpenStoryline`
- License first line:                                  Apache License
- File count: 168
- Has package.json: False
- Has requirements.txt: True
- Has install/download scripts: True
- Decision: Learn story/script pipeline shape; avoid automatic model downloads and shell scripts.

## ComfyUI

- Available locally: True
- Path: `local-tools/research-repos/ComfyUI`
- License first line:                     GNU GENERAL PUBLIC LICENSE
- File count: 1005
- Has package.json: False
- Has requirements.txt: True
- Has install/download scripts: False
- Decision: Use as optional local backend adapter, not as primary Director OS UX.

## ComfyUI-Manager

- Available locally: True
- Path: `local-tools/research-repos/ComfyUI-Manager`
- License first line:                     GNU GENERAL PUBLIC LICENSE
- File count: 135
- Has package.json: False
- Has requirements.txt: True
- Has install/download scripts: False
- Decision: Study security checks and registry ideas; do not install untrusted custom nodes by default.

## OpenMontage

- Available locally: False
- Path: `local-tools/research-repos/OpenMontage`
- License first line: UNKNOWN/not cloned
- File count: 0
- Has package.json: False
- Has requirements.txt: False
- Has install/download scripts: False
- Decision: Record as unresolved candidate; do not adopt until source is found and inspected.

## ViMax

- Available locally: False
- Path: `local-tools/research-repos/ViMax`
- License first line: UNKNOWN/not cloned
- File count: 0
- Has package.json: False
- Has requirements.txt: False
- Has install/download scripts: False
- Decision: Record as unresolved candidate; do not adopt until source is found and inspected.
