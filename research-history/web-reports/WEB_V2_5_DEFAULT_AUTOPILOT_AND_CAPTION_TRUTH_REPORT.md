# Director OS v2.5 Default Autopilot And Caption Truth Report

Generated: 2026-07-24T00:33:19.607688+00:00

## Default Experience

- Default route: `/studio/projects/burmese-music-video`
- Current project auto-load: yes
- Autopilot enabled: yes
- Normal primary action: CREATE / CONTINUE AUTOMATICALLY

## Inventory Reused

- Existing concepts: True
- Storyboard frames: 24
- Real AI image count: 0
- Composite frame count: 24
- Generated-video count: 18
- Prompt-package count: 24
- Captions found: 13
- Lip-sync segment records: 21

## Player And Captions

- Clean player: `/Users/chan/song-video-project/director-os/projects/burmese-music-video/previews/autopilot-v25/BEST_CLEAN_VIDEO.mp4`
- Verified-caption player: `/Users/chan/song-video-project/director-os/projects/burmese-music-video/previews/autopilot-v25/BEST_VERIFIED_CAPTIONED_VIDEO.mp4`
- Review/debug player: `/Users/chan/song-video-project/director-os/projects/burmese-music-video/previews/autopilot-v25/REVIEW_DEBUG_VIDEO.mp4`
- Clean player validation: ok
- Burmese font: Noto Sans Myanmar at `/System/Library/Fonts/NotoSansMyanmar.ttc`
- Font render status: passed
- V5 occurrence count: 21
- Verified caption count: 1
- Hidden inaccurate/untrusted caption count: 20
- Production caption status: blocked until all production gates pass
- Lip-sync-ready count: 0
- Lip-sync status: blocked by V5 caption truth gate

## Automatic Repairs

- Root route changed to load the current project directly.
- Main player defaults to clean video.
- Captioned player uses CAPTIONS_VERIFIED_ONLY, not unrestricted review captions.
- Review/debug video keeps all captions with status labels.
- Burmese font validation V2 created real image samples.
- Existing prompt packages were reused and augmented with caption truth/QC requirements.

## Remaining Approvals

- Local image model approval remains optional if real AI images are required.
- Cloud/video provider approval remains optional for final generation.
- Caption production approval remains blocked until unresolved lyric timing is repaired or confirmed.

## Exact Normal-User Next Action

Open `/`, review the current project page, press CREATE / CONTINUE AUTOMATICALLY, or refine with one sentence.
