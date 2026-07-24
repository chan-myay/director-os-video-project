# Director OS Web v0.8 Working Director Workspace Report

## Purpose

v0.8 turns the v0.7 static Command Center output into a working local director
workspace.

This version does not call APIs, upload media, generate video, publish, delete
media, install model weights, or run untrusted install scripts.

## Implemented Working Capabilities

### Persistent Autonomous Runs

Added database tables for:

- `director_runs`
- `storyboard_cards`
- `storyboard_decisions`
- `storyboard_comments`
- `previs_assets`
- `animatics`
- `renderer_strategy_items`
- `research_items`
- `motion_reference_analysis`
- `burmese_caption_lines`
- `pronunciation_overrides`
- `voice_tests`

The latest Director Plan can now be synced into persistent reviewable records.

### Real Raster Previs Composites

Created a standard-library PNG compositor. It writes real PNG files, not SVG
placeholders:

- `director-os/previs/latest/S001.png` through `S024.png`

Backend label:

- `stdlib_png_composite`

This is a local raster previs/composition backend, not AI image generation.

### Storyboard Workspace

Route:

- `/storyboard`

Working behavior:

- persistent cards
- PNG previs display
- approve/reject/needs-refine/planned decisions
- comments
- version increments
- decision history
- JSON/CSV exports

Exports:

- `director-os/plans/latest/STORYBOARD_WORKSPACE.json`
- `director-os/plans/latest/STORYBOARD_WORKSPACE.csv`

### Playable Animatic

Route:

- `/animatic`

Output:

- `director-os/animatics/latest/ANIMATIC.html`

Backend label:

- `html_timeline`

This is a playable local HTML animatic. It is not a rendered MP4 because ffmpeg
is not guaranteed on the current shell path.

### Motion Reference Assistance And Analysis

Route:

- `/motion-lab`

Working behavior:

- lists existing motion references
- runs metadata-only analysis
- records missing local files, invalid framing, and missing travel direction
- writes audit events

This does not download or scrape external videos.

### Burmese Captions / Pronunciation Workspace

Route:

- `/captions-voice`

Working behavior:

- seeds lyric lines from `lyrics/`
- preserves original text
- stores conservative normalized text
- stores caption text
- stores pronunciation-helper fields
- stores timing/status fields
- exports JSON/CSV

Exports:

- `director-os/captions/latest/BURMESE_CAPTION_WORKSPACE.json`
- `director-os/captions/latest/BURMESE_CAPTION_WORKSPACE.csv`

This is not a full Zawgyi-to-Unicode converter yet. It is a safe editable
workspace that preserves original lyrics.

### Voice Testing Workspace

Route:

- `/captions-voice`

Working behavior:

- records planned manual/cloud/local voice tests
- records consent and cloud-upload approval flags
- writes audit events

No voice API is called. No audio is generated.

### Renderer Strategy

Renderer strategy rows are persisted per storyboard card in
`renderer_strategy_items`.

The strategy differentiates:

- Seedance
- Kling Motion Control
- existing footage
- local raster previs
- manual fallback

Cloud paths remain blocked by privacy/spend/reference gates.

### Existing Production/QC Engine

The v0.1-v0.6B production engine remains available behind:

- `/advanced`
- `/jobs`
- `/exports`
- `/results`
- `/approval-gate`
- `/qc`
- `/audit-log`

## CLI

Added:

```bash
tools/director-os sync-workspace
tools/director-os build-animatic
tools/director-os review-status
```

Existing commands remain:

```bash
tools/director-os create "<idea>" --project /Users/chan/song-video-project
tools/director-os status /Users/chan/song-video-project
tools/director-os research /Users/chan/song-video-project
tools/director-os produce /Users/chan/song-video-project --dry-run
```

## Validation

Commands run:

```bash
python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)
cd director-os-web && python3 scripts/smoke_test_local.py
tools/director-os sync-workspace
tools/director-os review-status
```

Smoke test now verifies:

- v0.8 tables exist
- storyboard workspace syncs
- PNG previs files are created
- storyboard approval persists
- storyboard comments persist
- playable animatic file is written
- Burmese caption workspace seeds from lyrics
- voice-test record is created without API calls
- existing job/export/result/QC infrastructure still passes
- normal development DB counts are not changed by smoke tests

## Current Limitations

- Raster previs is procedural/composite, not AI-generated concept art.
- Animatic is HTML timeline, not MP4.
- Motion analysis is metadata/rule based unless a richer local vision backend is
  approved later.
- Burmese conversion is conservative and editable; full Zawgyi conversion is not
  implemented yet.
- Voice workspace records tests only; it does not call Azure, Google, local
  TTS, or voice-cloning systems.
- Renderer execution remains dry-run/manual-gated only.

## Next Highest-Value Step

Use `/storyboard` to approve/refine the 24 cards, then use `/motion-lab` to add
and analyze the F01 side-travel motion reference. That unlocks the most
important missing production input without uploading or generating anything.
