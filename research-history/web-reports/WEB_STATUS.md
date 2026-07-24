# Web Status

Version: `0.6B`

Status: local FastAPI production control room with SQLite workflow persistence
and approval-gated dry-run job packages with reference readiness validation and
text-only manual renderer exports plus local result import/QC/decision intake.

## What It Does

- Shows engine status.
- Shows product documents.
- Lists shot packs.
- Shows generated v0.2 request packages.
- Shows reference library strategy.
- Shows connector status.
- Shows approval gate and QC scorecard.
- Persists local workflow records.
- Saves approval gates.
- Saves QC reviews.
- Saves URL-only moodboard records.
- Writes audit logs.
- Creates frozen dry-run job packages.
- Runs connector dry-run validation only.
- Validates required F01 creative-lock references before real generation.
- Writes readiness reports.
- Creates text-only manual Seedance/Kling export packages.
- Imports locally generated result videos.
- Generates poster/contact sheet locally.
- Records structured result QC and permanent decisions.

## What It Does Not Do

- Generate video.
- Render.
- Upload media.
- Call paid APIs.
- Copy project media.
- Publish anything.
- Execute connector jobs.
- Use submitted/running/completed real connector states.
- Copy media into manual export folders.
- Call renderer APIs during result import.
- Modify the music-video edit automatically.

## Run

```bash
cd ~/song-video-project/director-os-web
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
./scripts/run_local.sh
```

## Smoke Test

```bash
cd ~/song-video-project/director-os-web
. .venv/bin/activate
python scripts/smoke_test_local.py
```
