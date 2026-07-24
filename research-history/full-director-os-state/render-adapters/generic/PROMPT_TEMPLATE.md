# Generic Renderer Adapter Template

Status: template only. Do not generate prompts or call APIs yet.

This adapter will later convert `RENDERER_FIELDS.yaml` into a generic renderer
request.

Fields to consume:

- `shot_id`
- `intent`
- `song_section`
- `references`
- `motion`
- `identity`
- `body_wardrobe`
- `location`
- `camera_lighting`
- `negative_rules`
- `qc`

Output later:

- concise renderer-neutral request
- selected references list
- reject conditions

No long prose prompt is created in v0.1.
