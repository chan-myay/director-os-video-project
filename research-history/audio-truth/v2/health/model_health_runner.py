
import json, os, time, traceback
from pathlib import Path
import torch, librosa
from transformers import AutoModelForCTC, AutoProcessor, AutoModelForSpeechSeq2Seq, AutoProcessor as WhisperProcessor
sample=Path(os.environ['SAMPLE'])
ctc_path=os.environ['CTC_PATH']
whisper_path=os.environ['WHISPER_PATH']
result={'ctc':{}, 'whisper':{}, 'ctc_alignment':{}}
audio, sr = librosa.load(str(sample), sr=16000, mono=True)
try:
    t=time.time(); proc=AutoProcessor.from_pretrained(ctc_path, local_files_only=True); model=AutoModelForCTC.from_pretrained(ctc_path, local_files_only=True)
    chars=''.join(sorted(set(os.environ.get('LYRIC_CHARS',''))))
    vocab=getattr(proc.tokenizer, 'get_vocab', lambda: {})()
    covered=sum(1 for ch in chars if ch in vocab)
    inputs=proc(audio, sampling_rate=16000, return_tensors='pt')
    with torch.no_grad():
        logits=model(**inputs).logits
    ids=torch.argmax(logits, dim=-1)
    decoded=proc.batch_decode(ids)[0]
    result['ctc']={'status':'passed','load_and_infer_seconds':round(time.time()-t,3),'decoded_text':decoded,'logit_shape':list(logits.shape),'tokenizer_char_coverage':{'covered':covered,'total':len(chars)}}
    result['ctc_alignment']={'status':'technically_possible','monotonic': True, 'method':'ctc_logits_available_for_known_text_alignment'}
except Exception as exc:
    result['ctc']={'status':'failed','error':str(exc),'traceback':traceback.format_exc()[-2000:]}
    result['ctc_alignment']={'status':'failed','error':str(exc)}
try:
    t=time.time(); proc2=WhisperProcessor.from_pretrained(whisper_path, local_files_only=True); model2=AutoModelForSpeechSeq2Seq.from_pretrained(whisper_path, local_files_only=True)
    features=proc2(audio, sampling_rate=16000, return_tensors='pt').input_features
    with torch.no_grad():
        predicted_ids=model2.generate(features, max_new_tokens=80)
    decoded2=proc2.batch_decode(predicted_ids, skip_special_tokens=True)[0]
    result['whisper']={'status':'passed','load_and_infer_seconds':round(time.time()-t,3),'decoded_text':decoded2,'hallucination_warning': len(decoded2.strip()) == 0}
except Exception as exc:
    result['whisper']={'status':'failed','error':str(exc),'traceback':traceback.format_exc()[-2000:]}
Path(os.environ['OUT']).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
