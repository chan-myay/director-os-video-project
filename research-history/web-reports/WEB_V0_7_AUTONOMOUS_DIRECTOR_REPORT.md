# Director OS Web v0.7 Autonomous Director Report

## Architecture Implemented

v0.7 pivots the primary experience from production administration to an
autonomous creative director workflow.

Implemented:

- FastAPI Command Center at `/`
- autonomous director service:
  `director-os-web/app/services/autonomous_director_service.py`
- local CLI:
  `tools/director-os`
- persistent canonical state in `director-os/state/`
- director output package in `director-os/plans/latest/`
- visual storyboard frame assets in `director-os/storyboards/latest/frames/`
- visual storyboard route at `/storyboard`
- Director Plan route at `/director-plan`
- Shot Plan route at `/shot-plan`
- Production continuation route at `/production`
- Research Assistant route at `/research-assistant`
- Advanced production controls preserved under `/advanced`

Existing v0.1-v0.6B infrastructure remains intact behind Advanced:
assets, shot packs, compiler, SQLite workflow state, approvals, gates, jobs,
manual exports, result import, QC, decisions, audit logs and promotion
manifests.

## GitHub Projects Inspected And Actual Findings

Shallow source clones were created under `local-tools/research-repos/`.
No install scripts were run. No model weights were downloaded.

Inspected:

- `soemind-forge`
  - License: MIT
  - Evidence: workflow templates, caption/text overlay guides, cost tracking,
    provider wrappers, Remotion-related package structure.
  - Reuse decision: learn workflow/caption/cost ideas; do not adopt
    Gemini-specific execution.
- `HKUDS-VideoAgent`
  - License: MIT
  - Evidence: Python project, requirements, multi-agent video intelligence
    framing, communication docs.
  - Reuse decision: learn orchestration/memory structure; do not adopt
    API-heavy execution directly.
- `FireRed-OpenStoryline`
  - License: Apache first line in license file
  - Evidence: FastAPI/CLI/storyline project with Dockerfile and download/install
    scripts.
  - Reuse decision: learn storyline-to-shot pipeline; do not run scripts or
    download models.
- `ComfyUI`
  - License: GPL
  - Evidence: modular graph engine, API/server structure, many blueprint
    examples including video/image workflows.
  - Reuse decision: optional local backend adapter only, not the main UX.
- `ComfyUI-Manager`
  - License: GPL
  - Evidence: registry/manager/security-check concepts.
  - Reuse decision: study security/registry ideas; do not install untrusted
    custom nodes by default.

OpenMontage and ViMax were not cloned because a reliable cloneable repository
was not identified in this pass. They are recorded as unresolved candidates,
not adopted.

Created:

- `director-os-research/GITHUB_ARCHITECTURE_AUDIT.md`
- `director-os-research/LICENSE_MATRIX.csv`
- `director-os-research/REUSABLE_COMPONENT_MAP.md`
- `director-os-research/SECURITY_AND_SUPPLY_CHAIN_REPORT.md`
- `director-os-research/BUILD_VS_ADOPT_DECISIONS.md`

## Reused Components And Licenses

No external code was imported into Director OS runtime.

Architecture ideas only:

- SoeMind Forge: MIT; workflow/caption/cost concepts.
- HKUDS VideoAgent: MIT; multi-agent orchestration concepts.
- FireRed-OpenStoryline: Apache; storyline pipeline concepts.
- ComfyUI / ComfyUI-Manager: GPL; optional adapter study only, no code copied.

## One-Line CLI Commands

```bash
tools/director-os create "<idea>" --project /Users/chan/song-video-project
tools/director-os continue /Users/chan/song-video-project
tools/director-os analyze /Users/chan/song-video-project
tools/director-os research /Users/chan/song-video-project
tools/director-os storyboard /Users/chan/song-video-project
tools/director-os plan-production /Users/chan/song-video-project
tools/director-os produce /Users/chan/song-video-project --dry-run
tools/director-os status /Users/chan/song-video-project
```

## Command Center Routes

- `/` - one idea + project folder Command Center
- `/director-plan` - creative summary and created package
- `/storyboard` - visual storyboard cards
- `/shot-plan` - song-aligned shot list
- `/production` - next production move
- `/research-assistant` - reference search map and GitHub audit trigger
- `/advanced` - old dashboard and production control access

## Autonomous Orchestrator Stages

The orchestrator currently runs these stages:

1. Project Archaeologist: reads key markdown/CSV/JSON evidence and filesystem
   structure.
2. Music Analyst: reuses existing song-energy JSON and section directives.
3. Burmese Lyric and Language Director: detects likely Zawgyi, preserves
   original text, creates normalized/caption-safe fields.
4. Creative Director: creates concepts and selects the best current concept.
5. Cinematographer/Lighting/Production Designer: writes bibles and visual plan.
6. Movement Director: maps movement needs and rejects uncontrolled choreography.
7. Storyboard Director: writes 24 storyboard cards and local SVG frames.
8. Renderer Strategist: ranks renderer/fallback per shot.
9. Editor: creates song-aligned edit plan and CSV.
10. Cost/Privacy/QC: preserves no-upload/no-generation approval boundaries.

## Project-State Format

Created:

- `director-os/state/PROJECT_STATE.json`
- `director-os/state/EVIDENCE_GRAPH.json`
- `director-os/state/DECISION_MEMORY.json`
- `director-os/state/FAILURE_MEMORY.json`
- `director-os/state/ASSET_INDEX.json`

State records include evidence source, confidence, status, reusable lessons,
approved/rejected/restricted decisions and project locks.

## Research Workflow

The research assistant returns search links, visual categories, movement
categories, composition/camera/lighting direction and rights warnings. It stores
no scraped copyrighted media.

Example:

```bash
tools/director-os research /Users/chan/song-video-project --query "Find mature side-travel performance references for a lonely blues-jazz bar music video."
```

## Visual Storyboard Functionality

Created:

- `director-os/plans/latest/STORYBOARD.json`
- `director-os/plans/latest/STORYBOARD_BOARD.html`
- `director-os/storyboards/latest/frames/S001.svg` through `S024.svg`
- `/storyboard` visual card workspace

Each card includes shot number, timecode, song section, purpose, framing, lens,
camera movement, lighting, production design, performer action, exact movement,
identity risk, body/motion risk, renderer and fallback.

Controls are displayed as disabled placeholders for approve/reject/refine until
versioned storyboard decisions are implemented.

## Local Image-Backend Status

Current backend is a mock/template SVG storyboard backend.

Hardware audit is stored in:

- `director-os/plans/latest/LOCAL_IMAGE_BACKEND_STATUS.md`

No large model weights were installed. ComfyUI was inspected as source only and
is not connected.

## Burmese Language Functionality

Implemented:

- original lyrics preservation
- likely Zawgyi detection
- Unicode-normalization placeholder without destructive spelling changes
- Burmese caption-safe line extraction
- typography guidance
- pronunciation-helper layer placeholder
- warning that pronunciation corrections must be user-editable and must not
  overwrite original lyrics

## Renderer-Selection Functionality

Every storyboard shot receives:

- recommended renderer
- fallback renderer
- required inputs
- identity exposure suitability
- motion/body risk
- privacy/cost warning

Seedance and Kling are differentiated. Kling Motion Control remains blocked
without an approved `character_start_frame`; Seedance remains blocked without an
approved motion-reference video.

## Edit-Plan Export Functionality

Created:

- `director-os/plans/latest/EDIT_PLAN.json`
- `director-os/plans/latest/EDIT_DECISION_PLAN.csv`
- `director-os/plans/latest/FULL_SHOT_LIST.csv`

The edit plan maps shots to song sections, timecodes, transitions, face-safe
coverage and caption notes. It does not alter the approved edit automatically.

## Existing-Project Dry Run Result

Command run:

```bash
tools/director-os create "Create a world-class cinematic Burmese music video for the existing song. My lead performer performs alone in the approved dark Finnish bar. The video must feel mature, elegant, emotionally intense, visually original and physically realistic. Continue from every approved asset, successful experiment, failed experiment and production lesson already in the folder. Build the complete director treatment, visual concept, music and lyric map, performance direction, movement plan, lighting, camera/lens language, storyboard, full shot list, editing plan, Burmese caption/voice plan and renderer strategy. Avoid karaoke, generic dance, martial arts, K-pop, TikTok, fake lip-sync and fake body proportions." --project /Users/chan/song-video-project
```

Result:

- Plan created: yes
- Storyboard cards: 24
- Shot count: 24
- Main concept: `The Bar Remembers Her`
- Next best action: review storyboard, then approve or record the F01
  side-travel motion reference.
- No paid API calls.
- No third-party uploads.
- No video generation.
- No publishing.
- No deletion.

## Questions Still Genuinely Required

The initial run asks three questions:

1. Approve or record one motion-reference video for F01 side-travel dance with
   exact timecode and rights/consent.
2. Approve or create one Kling character/start-frame plate only if Kling Motion
   Control will be tested.
3. Confirm whether captions should be Burmese-only or bilingual Burmese/English
   for the first public-facing version.

## Exact Test / Run Commands

```bash
python3 -m py_compile director-os-web/app/services/autonomous_director_service.py director-os-web/app/cli/director_os.py director-os-web/app/main.py
tools/director-os create "<idea>" --project /Users/chan/song-video-project
tools/director-os research /Users/chan/song-video-project --query "Find mature side-travel performance references for a lonely blues-jazz bar music video."
cd director-os-web && python3 scripts/smoke_test_local.py
cd director-os-web && ./scripts/run_local.sh
```

## Remaining Technical Limitations

- Visual storyboard cards are local template frames, not AI-generated concept
  art.
- No local model backend is installed or connected.
- Drag reorder/versioned storyboard decisions are UI placeholders.
- Burmese conversion is conservative and does not yet perform full
  Zawgyi-to-Unicode conversion.
- Voice comparison workspace is planned but not implemented.
- OpenMontage/ViMax remain unresolved until reliable source repositories are
  identified.
- PostgreSQL/object storage/worker abstractions are still architecture targets,
  not implemented migrations.

## Next Highest-Value Production Test

Use the new Director Plan and Storyboard to record or approve one F01
side-travel motion-reference video. That unlocks the most important missing
coverage while preserving the no-upload/no-generation safety boundary.
