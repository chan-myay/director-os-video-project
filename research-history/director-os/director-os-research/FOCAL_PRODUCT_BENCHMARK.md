# Focal Product Benchmark

Focal is treated as a closed-product workflow benchmark, not as a source-code dependency.

## Benchmarked Workflows

### One-Idea Creation

- User experience: enter one prompt and receive an expanded visual production.
- Director OS capability: `/studio-loop` creates a graph, runs local stages, assembles a preview, evaluates it, and repairs safe defects.
- Backend status: implemented in v2.0.
- Acceptance test: `tools/director-os studio-create "<idea>" --project /Users/chan/song-video-project`.

### Existing Script Expansion

- User experience: script becomes scenes and shots.
- Director OS capability: existing director plan, storyboard, shot graph and visual grammar.
- Backend status: partially implemented.
- Missing implementation: richer scene-by-scene conversational revision.

### Character Reuse

- User experience: same character persists across scenes.
- Director OS capability: approved identity references and privacy locks.
- Backend status: implemented as project truth, not yet operational in AI generation because no image model is installed.

### Location Reuse

- User experience: locations persist across generated scenes.
- Director OS capability: approved dark Finnish bar, winter window, Burmese art world and location bible.
- Backend status: implemented in planning and QC; real AI generation remains blocked on model/provider approval.

### Scene Generation

- User experience: scenes produce images/videos.
- Director OS capability: composite previs and FFmpeg animatic are operational; real AI image/video generation is not operational.
- Missing implementation: approved local/cloud generation backend.

### Conversational Editing

- User experience: user asks for changes in natural language.
- Director OS capability: storyboard refinement exists for one card; v2 loop repair framework records defects and repairs.
- Missing implementation: broad natural-language repair planner over all artifact types.

### Timeline Editing

- User experience: generated shots are arranged into a sequence.
- Director OS capability: full-song MP4 animatics, OTIO/EDL/DaVinci handoff.
- Backend status: implemented.

### Shot Replacement

- User experience: one bad shot can be replaced.
- Director OS capability: repair planner scopes repairs by defect; result import/QC/promotion manifests exist.
- Missing implementation: automatic provider-backed shot regeneration.

### Model Switching

- User experience: choose generation model per shot.
- Director OS capability: renderer strategy, connector status, manual exports and capability router.
- Backend status: planning/dry-run only until approvals.

### Generation History

- User experience: history of generations and versions.
- Director OS capability: director runs, animatic runs, result import, audit logs and studio loop events.
- Backend status: implemented.

### Consistency Controls

- User experience: preserve character, location and style.
- Director OS capability: project memory, approved/rejected assets, visual grammar, QC gates and failure memory.
- Backend status: implemented for planning/evaluation; generation still blocked by model/provider approval.

## Director OS Advantage Targets

Director OS should aim to exceed benchmark workflows through:

- persistent project memory
- Burmese-first language and cultural handling
- local-first privacy
- professional visual grammar
- renderer independence
- explicit failure memory
- self-testing and repair
- rights and consent controls

No superiority claim is made until evaluated visual outputs pass the acceptance gates.
