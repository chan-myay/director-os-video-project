from pathlib import Path
import os
import struct
import wave
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import creator_engine as e


def fake_nara(dir: Path):
    dir.mkdir(parents=True)
    (dir / "synthesize.py").write_text('''\
import argparse,wave
p=argparse.ArgumentParser()
p.add_argument('--voice');p.add_argument('--text');p.add_argument('--output');p.add_argument('--threads')
a=p.parse_args()
with wave.open(a.output,'wb') as f:
 f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000)
 f.writeframes(b"\\x00\\x00" * 24000)
''',encoding='utf-8')


def test_burmese_text_and_render(tmp_path,monkeypatch):
    monkeypatch.setenv('CREATOR_OUTPUT_ROOT',str(tmp_path / 'private'))
    fake_nara(tmp_path / 'nara')
    monkeypatch.setenv('NARA_MINI_ROOT',str(tmp_path / 'nara'))
    script='မသီတာက ဓာတ်ပုံ ၃ ပုံ ရိုက်ပါတယ်။ ဒီနေ့ ပျော်ရွှင်ပါတယ်။'
    job=e.new_job(script)
    e.render_job(job)
    result=e.read_status(job)
    assert result['status']=='complete',result
    assert result['subtitle_level']=='sentence'
    assert result['files']==['narration.mp3','video.mp4','captions.srt']
    assert (e.job_dir(job)/'video.mp4').stat().st_size>10_000
    assert 'မသီတာ' in (e.job_dir(job)/'captions.srt').read_text()
    assert len(e.segments(script))==2


def test_bad_paths_and_voice(tmp_path,monkeypatch):
    monkeypatch.setenv('CREATOR_OUTPUT_ROOT',str(tmp_path))
    for bad in ['..','../input','0'*32+'/../../','a'*33,'/tmp/a']:
        try:e.job_dir(bad)
        except ValueError:pass
        else:raise AssertionError(f'Accepted {bad}')
    try:e.new_job('hello','unknown')
    except ValueError:pass
    else:raise AssertionError('Accepted unknown voice')


def test_authentication(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.creator_server import app
    import base64
    monkeypatch.setenv('CREATOR_OUTPUT_ROOT',str(tmp_path))
    monkeypatch.setenv('CREATOR_USERNAME','tester')
    monkeypatch.setenv('CREATOR_PASSWORD','long private password')
    with TestClient(app) as c:
        assert c.get('/creator/').status_code==401
        auth='Basic '+base64.b64encode(b'tester:long private password').decode()
        r=c.get('/creator/',headers={'Authorization':auth})
        assert r.status_code==200
        assert 'Narrate this in Burmese' in r.text
        assert c.get('/creator/media/..%2Ffoo/video.mp4',headers={'Authorization':auth}).status_code in (400,404)