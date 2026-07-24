# Studio Loop 1 Report

Status: `awaiting_approval`
Score: `57.53`
Next action: Choose one local storyboard/ASR capability before final AI generation or trusted lyric alignment can pass.

## Defects
- `CAPTION_SYNC_UNVERIFIED` critical: Caption timing is not trusted for production.
- `LIPSYNC_PROVIDER_UNAVAILABLE` major: No phrase is ready for lip-sync packaging.
- `LOCAL_ASR_UNAVAILABLE` major: No local ASR evidence is available for Burmese singing alignment.
- `AI_GENERATION_UNAVAILABLE` major: Production AI frame count is zero.

## Repairs
- `rebuild_sync_calibrated_animatic` planned: Rebuild v15 full-song sync-calibrated review from brain timeline.
- `wait_for_lipsync_prerequisites` blocked: Lip-sync requires approved sync and provider setup.
- `request_local_asr_setup` requires_approval: Consolidated local ASR setup approval required for stronger lyric alignment.
- `request_local_storyboard_model` requires_approval: Consolidated local storyboard/image model approval required for real AI frames.
