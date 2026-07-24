# Music Video Director OS v0.1

Local control layer for the existing Burmese music video project.

This is not a renderer. It does not generate video, render edits, call cloud
APIs, or write long platform prompts. It turns project evidence into structured
shot packs that can later be translated into renderer-specific instructions
only after user approval.

## Locked Purpose

- Preserve the existing project.
- Use approved references only.
- Turn missing coverage into controlled shot packs.
- Keep identity, body, wardrobe, location, motion, and QC rules separate.
- Prevent rejected references and failed directions from re-entering production.

## Current Phase

v0.1 foundation and first seven missing-coverage shot packs.

## Hard Stops

- No new AI video generation.
- No Gemini/cloud/API usage.
- No render execution.
- No face correction.
- No lip-sync.
- No rejected references.
- No child-containing sources.
- No karaoke/lounge/microphone-centered direction.
- No fake singing or lip-sync.

## Main Entry Points

- `ENGINE_STATUS.md`
- `config/project_rules.yaml`
- `config/creative_lock.yaml`
- `motion-library/required_motion_references.csv`
- `shot-packs/`
- `qc/universal_qc_checklist.md`
- `command-center/NEXT_ACTION.md`
