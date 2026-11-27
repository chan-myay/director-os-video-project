#!/usr/bin/env python3
"""One-command private Burmese narration + video, no browser required."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.creator_engine import new_job, render_job, job_dir, read_status, SUPPORTED_VOICES

p=argparse.ArgumentParser(description='Director OS private Burmese creator')
p.add_argument('--text-file',type=Path,required=True,help='UTF-8 script file')
p.add_argument('--image',type=Path,help='Optional still image PNG/JPEG/WebP')
p.add_argument('--voice',choices=SUPPORTED_VOICES,default='ko-banyar')
a=p.parse_args()
script=a.text_file.read_text(encoding='utf-8')
image=a.image.read_bytes() if a.image else None
job=new_job(script,a.voice,visual=image,visual_name=a.image.name if a.image else '')
print('Job',job,flush=True)
try:
 render_job(job)
except Exception as exc:
 print('FAILED:',str(exc),file=sys.stderr);sys.exit(1)
r=read_status(job)
print('Status:',r['status'],'Audio seconds:',r['duration_seconds'])
for f in r['files']:
 print(job_dir(job)/f)