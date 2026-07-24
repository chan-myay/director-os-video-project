# v1.0.5 Internal Server Error Audit

## Failing Route

- Reported route: `http://127.0.0.1:8787/animatic`
- Reported symptom: `Internal Server Error`
- Also reported: old media URL `http://127.0.0.1:8787/director-assets/animatics/11/ANIMATIC_WITH_CAPTIONS.mp4` did not work.

## Reproduction Result In This Session

Initial curl result:

```text
curl -i http://127.0.0.1:8787/animatic
curl: (7) Failed to connect to 127.0.0.1 port 8787: Couldn't connect to server
```

The first reproducible failure in this session was not a stack trace; the local server was not reachable. A stale PID was reported on port `8787`, then had to be terminated before the app could be restarted.

## Root Cause

Two stability problems were present:

1. Server availability was unstable: port `8787` had a stale/unreachable process state.
2. The v1.0.4 `/animatic` page depended on a loose latest-context object and direct media links without a hardened resolver. Missing or defective animatic status files, missing MP4 files, or old/superseded versions could surface as broken pages instead of a useful state page.

## Fixed Files

- `director-os-web/app/services/latest_safe_animatic_service.py`
- `director-os-web/app/audio/auto_sync_service.py`
- `director-os-web/app/audio/lyric_audio_matcher.py`
- `director-os-web/app/audio/local_asr_service.py`
- `director-os-web/app/audio/sync_confidence_service.py`
- `director-os-web/app/main.py`
- `director-os-web/app/templates/animatic.html`
- `director-os-web/app/templates/auto_sync.html`
- `director-os-web/app/templates/music_analysis.html`
- `director-os-web/app/templates/listening_sync.html`
- `director-os-web/app/templates/font_check.html`
- `director-os-web/app/templates/command_center.html`
- `director-os-web/app/templates/voice_sync.html`
- `director-os-web/app/static/app.css`
- `director-os-web/app/cli/director_os.py`
- `director-os-web/scripts/smoke_test_local.py`

## Regression Test Added

The smoke test now checks:

- latest safe animatic resolver returns a version context
- existing old Run 11 media resolves if present
- missing animatic media returns useful 404 state
- path traversal is blocked
- auto lyric sync creates phrase suggestions
- boundary-only sync remains unverified/low-confidence
- Burmese font preview files are rendered
- caption v4 blocks low-confidence auto sync from production

Additional direct route/media check passed:

```text
/animatic 200
animatics/11/ANIMATIC_WITH_CAPTIONS.mp4 200 video/mp4
animatics/13/ANIMATIC_WITH_CAPTIONS_REVIEW.mp4 200 video/mp4
../START-HERE-TOMORROW.md 403 text/html
animatics/13/DOES_NOT_EXIST.mp4 404 text/html
```

## Current Route Status

- `/animatic`: renders successfully in direct route validation.
- Run 11 old media: preserved and serveable when the file exists.
- Run 13 latest media: serveable.
- Missing media: returns useful HTML 404 instead of traceback.
- Path traversal: blocked with 403.
