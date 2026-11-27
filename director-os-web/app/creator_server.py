"""Standalone private CPU-first creator entry point and mountable Director OS app.

For a public VPS run `uvicorn app.creator_server:app`, never legacy app.main,
which exposes historical project assets and lacks public-route authentication.
"""
from __future__ import annotations

import base64
import hmac
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.creator_engine import new_job, job_dir, read_status, render_job


# Serialized queue: one model inference / FFmpeg render at a time on a tiny VPS.
POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="burmese-creator")


class BasicPasswordGate(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user = os.environ.get("CREATOR_USERNAME")
        password = os.environ.get("CREATOR_PASSWORD")
        if not user or not password:
            return JSONResponse({"error": "Configure CREATOR_USERNAME and CREATOR_PASSWORD before serving"}, status_code=503)
        scheme, _, payload = request.headers.get("authorization", "").partition(" ")
        candidate_user = candidate_pass = ""
        if scheme.lower() == "basic":
            try:
                decoded = base64.b64decode(payload, validate=True).decode("utf-8")
                candidate_user, candidate_pass = decoded.split(":", 1)
            except (UnicodeDecodeError, ValueError, base64.binascii.Error):
                pass
        if not (hmac.compare_digest(candidate_user, user) and hmac.compare_digest(candidate_pass, password)):
            return JSONResponse({"error": "Authentication required"}, status_code=401, headers={"WWW-Authenticate": 'Basic realm="Director OS Creative Studio"', "Cache-Control": "no-store"})
        response = await call_next(request)
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response


creator_app = FastAPI(title="Director OS — Burmese Creator", docs_url=None, redoc_url=None, openapi_url=None)
creator_app.add_middleware(BasicPasswordGate)
app = FastAPI(title="Director OS — Private Creative Studio Entry", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/creator", creator_app)


FORM = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Director OS · Burmese Creator</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{background:#101622;color:#eaf0f9;font:16px system-ui,sans-serif;margin:0 auto;max-width:840px;padding:20px}
a{color:#98c7ff}.brand{font-size:14px;letter-spacing:.08em;color:#aab9cd}h1{margin:18px 0 6px;font-size:clamp(24px,5vw,36px)}p{color:#b6c5d4}
fieldset{border:1px solid #405064;border-radius:12px;padding:18px;margin-top:20px}label{display:block;margin:14px 0 7px;font-weight:600}
textarea{font-family:system-ui;line-height:1.9;width:100%;min-height:220px;resize:vertical}textarea,select,input{background:#182336;color:white;border:1px solid #607087;border-radius:7px;padding:11px}
button{background:#d3e4ff;color:#142130;font-weight:700;border:0;border-radius:8px;padding:14px 22px;cursor:pointer}button:disabled{opacity:.5;cursor:wait}
#results{padding:20px 0;min-height:40px}video,audio{width:100%;max-width:500px}.small{font-size:13px}
</style></head><body>
<div class="brand">DIRECTOR OS / CREATIVE STUDIO</div>
<h1>Narrate this in Burmese</h1>
<p>Paste your words. Generate a Ko Banyar narration, animated visual, and timed Burmese subtitles locally. No cloud image or video API.</p>
<form id="f"><fieldset><label for="text">Burmese script</label><textarea id="text" name="text" maxlength="5000" required lang="my" placeholder="မြန်မာစာကို ဒီမှာ ရေးပါ..."></textarea>
<label for="voice">Voice</label><select name="voice" id="voice"><option value="ko-banyar">Ko Banyar (Nara Mini v1)</option><option value="shoon">Shoon</option><option value="thazin">Thazin</option><option value="htet-myat">Htet Myat</option></select>
<label for="visual">Image (optional)</label><input type="file" id="visual" name="visual" accept="image/png,image/jpeg,image/webp">
<p class="small">Without an image, a simple graphic background is used. Visual rendering uses lightweight camera movement, not AI-generated video.</p>
<button id="make" type="submit">Create narrated video</button></fieldset></form>
<div id="results" aria-live="polite"></div>
<script>
const f=document.getElementById('f'), b=document.getElementById('make'), result=document.getElementById('results');
f.addEventListener('submit',async e=>{
 e.preventDefault();b.disabled=true;result.textContent='Submitting render…';
 try {
  const res=await fetch('/creator/jobs',{method:'POST',body:new FormData(f)});const j=await res.json();
  if(!res.ok)throw Error(j.error||'Could not create video');
  result.textContent='Rendering on the local CPU…';let done=false;
  while(!done){await new Promise(r=>setTimeout(r,1500));const s=await (await fetch('/creator/jobs/'+j.id)).json();
   if(s.status==='failed')throw Error(s.error||'Render failed');
   if(s.status==='complete'){
    done=true;result.replaceChildren();
    let title=document.createElement('h2');title.textContent='Your Burmese video';result.append(title);
    let video=document.createElement('video');video.controls=true;video.src='/creator/media/'+j.id+'/video.mp4';result.append(video);
    let audio=document.createElement('audio');audio.controls=true;audio.src='/creator/media/'+j.id+'/narration.mp3';result.append(audio);
    for(const [name,label] of [['video.mp4','Download MP4'],['narration.mp3','Download MP3'],['captions.srt','Download subtitles']]){
     let link=document.createElement('a');link.href='/creator/media/'+j.id+'/'+name;link.textContent=label;link.download=name;link.style.display='block';result.append(link);
    }
   }
  }
 }catch(err){result.textContent='Error: '+err.message;}finally{b.disabled=false;}
});
</script></body></html>"""


@app.get("/")
def landing():
    return RedirectResponse("/creator/", status_code=307)


@creator_app.get("/", response_class=HTMLResponse)
def creator_form():
    return HTMLResponse(FORM)


@creator_app.post("/jobs")
async def submit_render(request: Request):
    # Cap the complete HTTP body before multipart parsing to avoid memory spikes.
    declared = request.headers.get("content-length")
    if declared is None or not declared.isdecimal() or int(declared) > 26_000_000:
        return JSONResponse({"error": "Request too large or missing Content-Length"}, status_code=413)
    try:
        form = await request.form(max_files=1, max_fields=6)
        text = str(form.get("text", ""))
        voice = str(form.get("voice", "ko-banyar"))
        visual = form.get("visual")
        content = None
        filename = ""
        if visual is not None and getattr(visual, "filename", ""):
            content = await visual.read(25_000_001)
            filename = visual.filename
        job_id = new_job(text, voice, visual=content, visual_name=filename)
        POOL.submit(render_job, job_id)
        return JSONResponse({"id": job_id, "status": "queued"}, status_code=202)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception:
        return JSONResponse({"error": "Render submission failed"}, status_code=500)


@creator_app.get("/jobs/{job_id}")
def status(job_id: str):
    try:
        result = read_status(job_id)
        # no user text, disk paths, or private reference content in public metadata
        return {key: result[key] for key in ("id", "status", "duration_seconds", "files", "subtitle_level", "error") if key in result}
    except (FileNotFoundError, ValueError):
        return JSONResponse({"error": "Unknown job"}, status_code=404)


@creator_app.get("/media/{job_id}/{filename}")
def download(job_id: str, filename: str):
    if filename not in ("narration.mp3", "video.mp4", "captions.srt"):
        return JSONResponse({"error": "Not found"}, status_code=404)
    try:
        if read_status(job_id).get("status") != "complete":
            return JSONResponse({"error": "Job is not complete"}, status_code=409)
        file = job_dir(job_id) / filename
    except (FileNotFoundError, ValueError):
        return JSONResponse({"error": "Not found"}, status_code=404)
    if not file.is_file():
        return JSONResponse({"error": "File is missing"}, status_code=404)
    return FileResponse(file, filename=filename, media_type={"video.mp4":"video/mp4", "narration.mp3":"audio/mpeg", "captions.srt":"application/x-subrip"}[filename])