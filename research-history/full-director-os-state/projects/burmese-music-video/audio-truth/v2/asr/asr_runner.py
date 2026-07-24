
import json, os, time, traceback
from pathlib import Path
import torch, librosa
from transformers import AutoProcessor, AutoModelForCTC, AutoModelForSpeechSeq2Seq
windows=json.loads(Path(os.environ['WINDOWS']).read_text())
ctc_path=os.environ['CTC_PATH']; whisper_path=os.environ['WHISPER_PATH']
result={'models':[], 'segments':[]}
try:
    proc=AutoProcessor.from_pretrained(ctc_path, local_files_only=True); model=AutoModelForCTC.from_pretrained(ctc_path, local_files_only=True)
    for w in windows:
        audio, sr=librosa.load(w['path'], sr=16000, mono=True)
        t=time.time(); inputs=proc(audio, sampling_rate=16000, return_tensors='pt')
        with torch.no_grad(): logits=model(**inputs).logits
        ids=torch.argmax(logits, dim=-1); text=proc.batch_decode(ids)[0]
        result['segments'].append({'model':'YonaKhine/finetuned-w2v2-bert-burmese-asr','audio_source':w['path'],'start':w['start'],'end':w['end'],'raw_burmese_transcript':text,'normalized_transcript':' '.join(text.split()),'confidence':None,'runtime':round(time.time()-t,3),'logit_shape':list(logits.shape),'repetition_warning':len(set(text.split())) < max(1, len(text.split())//4) if text.split() else False})
    result['models'].append({'model':'YonaKhine/finetuned-w2v2-bert-burmese-asr','status':'completed','revision':os.environ['CTC_REV']})
except Exception as exc:
    result['models'].append({'model':'YonaKhine/finetuned-w2v2-bert-burmese-asr','status':'failed','error':str(exc),'traceback':traceback.format_exc()[-2000:]})
try:
    proc2=AutoProcessor.from_pretrained(whisper_path, local_files_only=True); model2=AutoModelForSpeechSeq2Seq.from_pretrained(whisper_path, local_files_only=True)
    for w in windows[:8]:
        audio, sr=librosa.load(w['path'], sr=16000, mono=True)
        t=time.time(); features=proc2(audio, sampling_rate=16000, return_tensors='pt').input_features
        with torch.no_grad(): ids=model2.generate(features, max_new_tokens=80)
        text=proc2.batch_decode(ids, skip_special_tokens=True)[0]
        result['segments'].append({'model':'chuuhtetnaing/whisper-small-myanmar','audio_source':w['path'],'start':w['start'],'end':w['end'],'raw_burmese_transcript':text,'normalized_transcript':' '.join(text.split()),'confidence':None,'runtime':round(time.time()-t,3),'hallucination_warning':len(text.strip())==0})
    result['models'].append({'model':'chuuhtetnaing/whisper-small-myanmar','status':'completed','revision':os.environ['WHISPER_REV']})
except Exception as exc:
    result['models'].append({'model':'chuuhtetnaing/whisper-small-myanmar','status':'failed','error':str(exc),'traceback':traceback.format_exc()[-2000:]})
Path(os.environ['OUT']).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
