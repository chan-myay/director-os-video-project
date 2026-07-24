# Director OS v2.4.1 Real Anchor And Playback Repair Report

Generated: 2026-07-13T16:22:27.234301+00:00

## User Acceptance Evidence

- Previous anchor set: invalidated_by_real_user_review
- Early anchor: accepted_correct and preserved as human_verified_early_anchor
- Previous middle anchor: invalid_no_clear_vocal_or_caption_late
- Previous late anchor: invalid_alignment
- Previous large preview: playback_or_content_failure

## Replacement Anchors

- Middle replacement: `lyric_line_7a8eb022_occurrence_1`
- Late replacement: `lyric_line_6545c465_occurrence_2`
- Anchor validation file: `/Users/chan/song-video-project/director-os/projects/burmese-music-video/audio-truth/v4/anchors/ANCHOR_VALIDATION.json`
- Anchor candidates file: `/Users/chan/song-video-project/director-os/state/AUDIO_TRUTH_ANCHOR_CANDIDATES.json`

## Playback Repair

V4 preview was rebuilt as H.264/AAC/yuv420p with `+faststart`.

- Preview URL: `http://127.0.0.1:8787/studio-assets/burmese-music-video/previews/audio-truth-v4/CREATIVE_SKETCH_AUDIO_TRUTH_V4_WITH_CAPTIONS.mp4`
- Duration status: ok
- Browser-compatible codec check: True
- Faststart/seekability proxy: True
- HTTP status during live route test: 200
- Range status during live route test: 206
- Playback ready: False
- Browser automation: headless Chrome loaded metadata and seeked near the end, but playback time did not advance in headless mode. MP4 route/range/codec/full-duration validation passed; real interactive browser play-start remains the remaining check.

## Timeline V4

- High confidence: 13
- Medium confidence: 8
- Low confidence: 0
- Blocked: 0
- Lip-sync-ready occurrence count: 9
- Production captions ready: False

## Caption Defects And Repairs

- Caption defects found: 2
- Repairs performed: invalidated broken V3 anchors, preserved early human anchor, reselected middle/late through validity gate, rebuilt V4 captions, rebuilt V4 browser-compatible preview, regenerated V4 lip-sync segment gates.

## SoeMind Forge Adaptation

- Report: `/Users/chan/song-video-project/director-os-research/SOEMIND_FORGE_ADAPTATION_V2_4_1.md`
- Adapted/adopted workflow features: 8
- Cloud/provider assumptions rejected for this local-first repair.

## Next Action

Review the two replacement Audio Truth anchors. The first anchor is already trusted evidence. If the large preview still does not play interactively, use the direct video link shown on the page; the remaining unproven condition is browser play-start, not file integrity/range/codec/duration.

No new model download, cloud upload, paid API call, InfiniteTalk install, image/video model install, source lyric overwrite, or master-audio overwrite occurred.
