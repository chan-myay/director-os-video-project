# Director OS Web

Local-first FastAPI product shell for Director OS v0.3.

This app reads local engine/product files and displays status. It does not copy
media, upload references, call paid APIs, generate video, or render.

## Setup

```bash
cd ~/song-video-project/director-os-web
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
./scripts/run_local.sh
```

Then open:

```text
http://127.0.0.1:8787
```

## Safety

All connector pages are read-only status pages in v0.3.
