# SoeMind Forge Adaptation v2.4.1

Repository: `/Users/chan/song-video-project/local-tools/research-repos/soemind-forge`
Inspected commit: `42e055367d12346e27cb4aa1470b3d3a2bbf8d37`

No setup scripts, provider calls, cloud uploads, or private-media exports were executed.

| Feature | Decision | Director OS connection |
|---|---|---|
| one plain-English production command | adapted | Studio keeps CREATE EVERYTHING / repair loop as the user-facing command. |
| content preflight before generation | adopted | Audio Truth V4 invalidates broken anchors before rebuilding. |
| locked reusable asset registry | already exists | Director OS preserves approved/rejected references and canonical lyric source. |
| character/face consistency by asset ID | already exists | Project evidence IDs remain authoritative; not used for audio repair. |
| preview-before-expensive-render | adapted | V4 creates local anchor/preview MP4s before any renderer or InfiniteTalk. |
| content review after generation | adopted | Anchor validity and playback validation run before UI promotion. |
| task recipes/skills | adapted | Audio Truth Repair recipe added to Studio status. |
| budget cap and spend ledger | already exists | No spend path used in v2.4.1. |
| output packaging | adapted | V4 packages captions, preview, anchor clips, validation, and lip-sync segments. |
| local post-production text rendering | adopted | ASS subtitles rendered locally with FFmpeg. |
| agent instructions continue through QA and packaging | adopted | V4 script runs invalidate -> regenerate -> validate -> package -> report. |
| cloud-first generation assumptions | rejected | Director OS remains local-first and does not use providers here. |

Applied pattern: content preflight and content review now gate Audio Truth anchors before they are presented in the Studio UI.
