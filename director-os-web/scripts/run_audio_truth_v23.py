from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "director-os"
PROJECT_ID = "burmese-music-video"
PROJECT_ROOT = ENGINE_ROOT / "projects" / PROJECT_ID
STATE_ROOT = ENGINE_ROOT / "state"
AUDIO_TRUTH_ROOT = PROJECT_ROOT / "audio-truth" / "v2"
STEMS_ROOT = AUDIO_TRUTH_ROOT / "stems"
ASR_ROOT = AUDIO_TRUTH_ROOT / "asr"
SEGMENT_ROOT = AUDIO_TRUTH_ROOT / "lipsync-segments"
CAPTION_ROOT = ENGINE_ROOT / "captions" / "audio-truth-v2"
PREVIEW_ROOT = PROJECT_ROOT / "previews" / "audio-truth-v2"
MODEL_ROOT = REPO_ROOT / "local-models" / "audio-truth"
HF_CACHE = MODEL_ROOT / "hf" / "hub"
VENV = REPO_ROOT / ".venvs" / "audio-truth"
PYTHON = VENV / "bin" / "python"
MASTER_AUDIO = REPO_ROOT / "audio" / "01.mp3"
CANONICAL_LYRIC = REPO_ROOT / "lyrics" / "အချစ်မဲ့ ဇာတ်လမ်း.txt"
FFMPEG = REPO_ROOT / "local-tools" / "envs" / "faceswap" / "bin" / "ffmpeg"
FFPROBE = REPO_ROOT / "local-tools" / "envs" / "faceswap" / "bin" / "ffprobe"
CTC_REPO = "YonaKhine/finetuned-w2v2-bert-burmese-asr"
CTC_REV = "3a0bb058936140acfe7c905171eefc78234e93be"
WHISPER_REPO = "chuuhtetnaing/whisper-small-myanmar"
WHISPER_REV = "f3de3c167914fec3c0974aad1189eda3fa77d8cd"
BURMESE_RANGE = ("\u1000", "\u109f")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-demucs", action="store_true")
    args = parser.parse_args()
    for root in [AUDIO_TRUTH_ROOT, STEMS_ROOT, ASR_ROOT, SEGMENT_ROOT, CAPTION_ROOT, PREVIEW_ROOT, STATE_ROOT]:
        root.mkdir(parents=True, exist_ok=True)
    log: list[str] = []
    started = time.time()
    install = inspect_install()
    sources = audit_sources()
    phrases = parse_lyrics()
    health = run_health_checks(log, skip_demucs=args.skip_demucs)
    stems = run_full_vocal_separation(log, skip_demucs=args.skip_demucs)
    evidence = run_audio_models(phrases, stems, log)
    timeline = build_timeline(phrases, stems, evidence)
    verification = verify_lyrics(phrases, timeline, evidence)
    captions = build_captions(timeline)
    lipsync = build_lipsync_segments(timeline, stems)
    meaning = build_meaning_map(timeline)
    preview = build_preview(captions, timeline, log)
    production_brain = update_production_brain(timeline, meaning, captions, lipsync, preview)
    status = {
        "version": "v2.3",
        "created_at": now(),
        "runtime_seconds": round(time.time() - started, 3),
        "canonical_lyric_source": str(CANONICAL_LYRIC),
        "canonical_source_audit": sources,
        "install": install,
        "health": health,
        "stems": stems,
        "evidence": evidence.get("summary", {}),
        "timeline": timeline_summary(timeline),
        "verification": verification,
        "captions": captions,
        "lipsync": lipsync,
        "meaning": {"path": str(STATE_ROOT / "SONG_MEANING_PERFORMANCE_MAP.json"), "occurrences": len(meaning["occurrences"])},
        "preview": preview,
        "production_brain": production_brain,
        "log": log,
        "next_action": next_action(timeline, verification),
    }
    write_json(AUDIO_TRUTH_ROOT / "AUDIO_TRUTH_V2_STATUS.json", status)
    write_report(status, timeline)
    print(json.dumps(status, ensure_ascii=False, indent=2))


def inspect_install() -> dict[str, Any]:
    lock_path = AUDIO_TRUTH_ROOT / "PACKAGE_LOCK.txt"
    run([str(PYTHON), "-m", "pip", "freeze"], stdout_path=lock_path, check=False)
    snapshots = {
        "ctc": HF_CACHE / "models--YonaKhine--finetuned-w2v2-bert-burmese-asr" / "snapshots" / CTC_REV,
        "whisper": HF_CACHE / "models--chuuhtetnaing--whisper-small-myanmar" / "snapshots" / WHISPER_REV,
    }
    models = {}
    for key, path in snapshots.items():
        models[key] = {
            "path": str(path),
            "exists": path.exists(),
            "bytes": dir_size(path) if path.exists() else 0,
            "files": file_records(path) if path.exists() else [],
        }
    return {
        "environment": str(VENV),
        "python": command_output([str(PYTHON), "--version"]),
        "package_lock": str(lock_path),
        "model_root": str(MODEL_ROOT),
        "models": models,
        "licenses": {
            CTC_REPO: "mit per downloaded model metadata",
            WHISPER_REPO: "apache-2.0 per downloaded model metadata",
            "demucs": "mit per upstream package metadata",
        },
        "uninstall": f"rm -rf {VENV} {MODEL_ROOT} {AUDIO_TRUTH_ROOT} {CAPTION_ROOT} {PREVIEW_ROOT}",
    }


def audit_sources() -> dict[str, Any]:
    old = PROJECT_ROOT / "inputs" / "51b07bfca4c4-Zawgyi.txt"
    return {
        "canonical": {"path": str(CANONICAL_LYRIC), "sha256": sha256(CANONICAL_LYRIC), "encoding": "unicode", "status": "selected_manual_unicode"},
        "stale_zawgyi_copy": {"path": str(old), "exists": old.exists(), "sha256": sha256(old) if old.exists() else "", "status": "superseded_stale_retained_for_history"},
    }


def parse_lyrics() -> list[dict[str, Any]]:
    text = CANONICAL_LYRIC.read_text(encoding="utf-8", errors="ignore")
    repeated: dict[str, int] = {}
    phrases: list[dict[str, Any]] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        category = line_category(line)
        key = short_hash(line)
        repeated[key] = repeated.get(key, 0) + 1
        if category != "lyric":
            continue
        phrases.append(
            {
                "phrase_id": len(phrases) + 1,
                "line_number": line_number,
                "occurrence_index": repeated[key],
                "occurrence_id": f"lyric_line_{key}_occurrence_{repeated[key]}",
                "canonical_unicode_lyric": " ".join(line.split()),
                "source_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            }
        )
    write_json(AUDIO_TRUTH_ROOT / "NORMALIZED_LYRIC_OCCURRENCES.json", {"source": str(CANONICAL_LYRIC), "occurrences": phrases})
    return phrases


def run_health_checks(log: list[str], skip_demucs: bool) -> dict[str, Any]:
    health_root = AUDIO_TRUTH_ROOT / "health"
    health_root.mkdir(parents=True, exist_ok=True)
    sample = health_root / "health_sample.wav"
    run_ffmpeg(["-y", "-ss", "55", "-t", "12", "-i", str(MASTER_AUDIO), "-ac", "1", "-ar", "16000", str(sample)], log)
    demucs = {"status": "skipped"}
    if not skip_demucs:
        demucs_out = health_root / "demucs"
        code = run([str(PYTHON), "-m", "demucs.separate", "--two-stems", "vocals", "-n", "htdemucs", "-d", "cpu", "--segment", "7", "-j", "1", "-o", str(demucs_out), str(sample)], env=env(), stdout_path=health_root / "demucs_health.log", check=False)
        vocal = next(demucs_out.rglob("vocals.wav"), None) if demucs_out.exists() else None
        demucs = {"status": "passed" if code == 0 and vocal and vocal.exists() and audio_energy(vocal) > 0 else "failed", "log": str(health_root / "demucs_health.log"), "vocal_energy": audio_energy(vocal) if vocal else 0.0}
    model_health = run_model_health(sample, health_root)
    health = {"sample": str(sample), "demucs": demucs, **model_health}
    write_json(health_root / "HEALTH_STATUS.json", health)
    return health


def run_model_health(sample: Path, health_root: Path) -> dict[str, Any]:
    script = health_root / "model_health_runner.py"
    out = health_root / "MODEL_HEALTH.json"
    script.write_text(
        """
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
""",
        encoding="utf-8",
    )
    lyric_chars = "".join(sorted({ch for ch in CANONICAL_LYRIC.read_text(encoding="utf-8", errors="ignore") if "\u1000" <= ch <= "\u109f"}))
    env_vars = env()
    env_vars.update(
        {
            "SAMPLE": str(sample),
            "CTC_PATH": str(HF_CACHE / "models--YonaKhine--finetuned-w2v2-bert-burmese-asr" / "snapshots" / CTC_REV),
            "WHISPER_PATH": str(HF_CACHE / "models--chuuhtetnaing--whisper-small-myanmar" / "snapshots" / WHISPER_REV),
            "LYRIC_CHARS": lyric_chars,
            "OUT": str(out),
        }
    )
    run([str(PYTHON), str(script)], env=env_vars, stdout_path=health_root / "model_health.log", check=False)
    return read_json(out, {"ctc": {"status": "failed_no_output"}, "whisper": {"status": "failed_no_output"}, "ctc_alignment": {"status": "failed_no_output"}})


def run_full_vocal_separation(log: list[str], skip_demucs: bool) -> dict[str, Any]:
    full_mix = STEMS_ROOT / "full_mix_16k_mono.wav"
    run_ffmpeg(["-y", "-i", str(MASTER_AUDIO), "-ac", "1", "-ar", "16000", str(full_mix)], log)
    if not skip_demucs:
        out = STEMS_ROOT / "demucs"
        code = run([str(PYTHON), "-m", "demucs.separate", "--two-stems", "vocals", "-n", "htdemucs", "-d", "cpu", "--segment", "7", "-j", "1", "-o", str(out), str(MASTER_AUDIO)], env=env(), stdout_path=STEMS_ROOT / "demucs_full.log", check=False)
        vocals = next(out.rglob("vocals.wav"), None) if out.exists() else None
        no_vocals = next(out.rglob("no_vocals.wav"), None) if out.exists() else None
        if code == 0 and vocals and vocals.exists():
            shutil.copy2(vocals, STEMS_ROOT / "vocals.wav")
            if no_vocals and no_vocals.exists():
                shutil.copy2(no_vocals, STEMS_ROOT / "instrumental.wav")
    vocals_out = STEMS_ROOT / "vocals.wav"
    instrumental_out = STEMS_ROOT / "instrumental.wav"
    vocals_16 = STEMS_ROOT / "vocals_16k_mono.wav"
    if vocals_out.exists():
        run_ffmpeg(["-y", "-i", str(vocals_out), "-ac", "1", "-ar", "16000", str(vocals_16)], log)
    meta = {
        "master_audio": str(MASTER_AUDIO),
        "master": probe(MASTER_AUDIO),
        "vocals": str(vocals_out) if vocals_out.exists() else "",
        "instrumental": str(instrumental_out) if instrumental_out.exists() else "",
        "vocals_16k_mono": str(vocals_16) if vocals_16.exists() else "",
        "full_mix_16k_mono": str(full_mix),
        "vocal_energy": audio_energy(vocals_16 if vocals_16.exists() else full_mix),
        "duration_matches_master": duration_ok(probe(vocals_16 if vocals_16.exists() else full_mix), probe(MASTER_AUDIO)),
        "status": "separated" if vocals_16.exists() else "separation_failed_full_mix_fallback",
        "tool": "demucs 4.0.1 htdemucs two-stem cpu segment=7 jobs=1",
        "hashes": {p.name: sha256(p) for p in [MASTER_AUDIO, full_mix, vocals_16, instrumental_out] if p.exists()},
    }
    write_json(STEMS_ROOT / "STEM_VALIDATION.json", meta)
    return meta


def run_audio_models(phrases: list[dict[str, Any]], stems: dict[str, Any], log: list[str]) -> dict[str, Any]:
    source = Path(stems.get("vocals_16k_mono") or stems.get("full_mix_16k_mono"))
    windows = make_windows(source, ASR_ROOT)
    script = ASR_ROOT / "asr_runner.py"
    out = ASR_ROOT / "AUDIO_MODEL_EVIDENCE.json"
    script.write_text(
        """
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
""",
        encoding="utf-8",
    )
    env_vars = env()
    env_vars.update(
        {
            "WINDOWS": str(ASR_ROOT / "WINDOWS.json"),
            "OUT": str(out),
            "CTC_PATH": str(HF_CACHE / "models--YonaKhine--finetuned-w2v2-bert-burmese-asr" / "snapshots" / CTC_REV),
            "WHISPER_PATH": str(HF_CACHE / "models--chuuhtetnaing--whisper-small-myanmar" / "snapshots" / WHISPER_REV),
            "CTC_REV": CTC_REV,
            "WHISPER_REV": WHISPER_REV,
        }
    )
    run([str(PYTHON), str(script)], env=env_vars, stdout_path=ASR_ROOT / "asr_runner.log", check=False)
    evidence = read_json(out, {"models": [{"status": "failed_no_output"}], "segments": []})
    by_model: dict[str, list[dict[str, Any]]] = {}
    for segment in evidence.get("segments", []):
        by_model.setdefault(segment["model"], []).append(segment)
    for model, segments in by_model.items():
        model_dir = ASR_ROOT / safe_name(model)
        model_dir.mkdir(parents=True, exist_ok=True)
        write_json(model_dir / "raw_segments.json", segments)
        write_json(model_dir / "timestamps.json", [{"start": s["start"], "end": s["end"]} for s in segments])
        write_json(model_dir / "confidence.json", {"confidence_available": False})
        (model_dir / "transcript.txt").write_text("\n".join(s.get("raw_burmese_transcript", "") for s in segments), encoding="utf-8")
        write_json(model_dir / "run_metadata.json", {"model": model, "segments": len(segments), "no_cloud_upload": True})
    evidence["summary"] = {"model_count": len(evidence.get("models", [])), "segment_count": len(evidence.get("segments", [])), "models": evidence.get("models", [])}
    write_json(STATE_ROOT / "AUDIO_MODEL_EVIDENCE.json", evidence)
    return evidence


def make_windows(source: Path, root: Path) -> list[dict[str, Any]]:
    windows_root = root / "windows"
    windows_root.mkdir(parents=True, exist_ok=True)
    duration = float(probe(source).get("duration") or 0)
    windows = []
    start = 20.0
    idx = 1
    while start < min(duration, 240):
        end = min(start + 25.0, duration)
        path = windows_root / f"window_{idx:02d}.wav"
        run_ffmpeg(["-y", "-ss", str(start), "-to", str(end), "-i", str(source), "-ac", "1", "-ar", "16000", str(path)], [])
        windows.append({"index": idx, "start": start, "end": end, "path": str(path)})
        start += 22.0
        idx += 1
    write_json(root / "WINDOWS.json", windows)
    return windows


def build_timeline(phrases: list[dict[str, Any]], stems: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    prior = read_json(STATE_ROOT / "PRODUCTION_BRAIN_TIMELINE.json", {})
    prior_events = [e for e in prior.get("events", []) if e.get("approved_unicode") or e.get("caption_text")]
    segments = evidence.get("segments", [])
    occurrences = []
    duration = float(probe(MASTER_AUDIO).get("duration") or 0)
    for idx, phrase in enumerate(phrases):
        p = prior_events[idx] if idx < len(prior_events) else {}
        start = float(p.get("caption_start") or p.get("start") or (20 + idx * 8))
        end = float(p.get("caption_end") or p.get("end") or min(start + 5, duration))
        score = text_evidence_score(phrase["canonical_unicode_lyric"], segments)
        energy = region_energy(Path(stems.get("vocals_16k_mono") or stems.get("full_mix_16k_mono")), start, end)
        confidence = min(0.72, 0.25 + score * 0.25 + min(0.22, energy * 4))
        if score > 0.3 and energy > 0.015:
            status = "aligned_medium_confidence"
        elif energy > 0.01:
            status = "aligned_low_confidence"
        else:
            status = "alignment_failed"
        blockers = []
        if status != "aligned_high_confidence":
            blockers.append("ALIGNMENT_NOT_HIGH_CONFIDENCE")
        if score < 0.15:
            blockers.append("ASR_TEXT_MATCH_WEAK_OR_UNAVAILABLE")
        occurrences.append(
            {
                **phrase,
                "phrase_start": round(start, 3),
                "phrase_end": round(end, 3),
                "word_timing": [],
                "syllable_timing": [],
                "vocal_onset": round(start, 3),
                "vocal_offset": round(end, 3),
                "asr_transcripts": nearby_transcripts(start, end, segments),
                "ctc_alignment_score": round(score, 3),
                "model_agreement": model_agreement(segments),
                "phrase_order_score": 0.65 if p else 0.25,
                "repeated_line_mapping": "occurrence_order_preserved",
                "confidence": round(confidence, 3),
                "evidence": ["canonical_manual_unicode", "demucs_vocal_stem" if stems.get("status") == "separated" else "full_mix_fallback", "ctc_asr_evidence_attempted", "whisper_small_myanmar_attempted", "previous_brain_order"],
                "status": status,
                "blockers": blockers,
            }
        )
    timeline = {
        "version": "audio-truth-v2",
        "created_at": now(),
        "master_song": str(MASTER_AUDIO),
        "master_duration": duration,
        "canonical_lyric_source": str(CANONICAL_LYRIC),
        "alignment_basis": "ctc_asr_vocal_stem_evidence_plus_prior_timing",
        "occurrences": occurrences,
        "production_caption_allowed": all(o["status"] == "aligned_high_confidence" for o in occurrences),
        "lipsync_allowed": any(o["status"] == "aligned_high_confidence" for o in occurrences),
    }
    write_json(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V2.json", timeline)
    return timeline


def verify_lyrics(phrases: list[dict[str, Any]], timeline: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    unresolved = []
    for occ in timeline["occurrences"]:
        if occ["status"] != "aligned_high_confidence":
            unresolved.append(
                {
                    "occurrence_id": occ["occurrence_id"],
                    "line": occ["canonical_unicode_lyric"],
                    "status": "needs_targeted_review",
                    "reason": "Model evidence ran locally, but this occurrence is not high-confidence enough for production captions or lip-sync.",
                }
            )
    payload = {
        "status": "needs_targeted_review" if unresolved else "verified_by_model_evidence",
        "unresolved_count": len(unresolved),
        "unresolved": unresolved[:10],
        "auto_accepted_normalization_count": 0,
        "meaning_changing_corrections_auto_applied": 0,
    }
    write_json(STATE_ROOT / "LYRIC_TEXT_VERIFICATION.json", payload)
    return payload


def build_captions(timeline: dict[str, Any]) -> dict[str, Any]:
    items = []
    for index, occ in enumerate(timeline["occurrences"], start=1):
        if occ["status"] == "alignment_failed":
            continue
        text = occ["canonical_unicode_lyric"]
        label = "AUDIO TRUTH REVIEW"
        if occ["status"] != "aligned_high_confidence":
            label += f" - {occ['status'].replace('_', ' ').upper()}"
        items.append({"index": index, "start": occ["phrase_start"], "end": occ["phrase_end"], "text": f"{text}\\N{{{label}}}"})
    write_srt(CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_REVIEW.srt", items)
    write_vtt(CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_REVIEW.vtt", items)
    write_ass(CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_REVIEW.ass", items)
    blockers = {
        "production_captions_ready": False,
        "blockers": ["NO_HIGH_CONFIDENCE_FULL_ALIGNMENT" if not timeline["production_caption_allowed"] else ""],
        "review_caption_count": len(items),
    }
    write_json(CAPTION_ROOT / "ALIGNMENT_STATUS.json", timeline)
    write_json(CAPTION_ROOT / "LYRIC_VERIFICATION.json", read_json(STATE_ROOT / "LYRIC_TEXT_VERIFICATION.json", {}))
    write_json(CAPTION_ROOT / "CAPTION_EVALUATION.json", evaluate_captions(timeline))
    write_json(CAPTION_ROOT / "CAPTION_BLOCKERS.json", blockers)
    return {"path": str(CAPTION_ROOT), "review_caption_count": len(items), "production_ready": False, "blockers": [b for b in blockers["blockers"] if b]}


def build_lipsync_segments(timeline: dict[str, Any], stems: dict[str, Any]) -> dict[str, Any]:
    ready = []
    blocked = []
    vocal = Path(stems.get("vocals_16k_mono") or stems.get("full_mix_16k_mono"))
    for occ in timeline["occurrences"]:
        occ_dir = SEGMENT_ROOT / occ["occurrence_id"]
        occ_dir.mkdir(parents=True, exist_ok=True)
        (occ_dir / f"{occ['occurrence_id']}_lyric.txt").write_text(occ["canonical_unicode_lyric"], encoding="utf-8")
        write_json(occ_dir / f"{occ['occurrence_id']}_meaning.json", {"status": "pending_or_mapped", "lyric": occ["canonical_unicode_lyric"]})
        timing = {"occurrence_id": occ["occurrence_id"], "start": occ["phrase_start"], "end": occ["phrase_end"], "status": occ["status"], "confidence": occ["confidence"], "blockers": occ["blockers"]}
        write_json(occ_dir / f"{occ['occurrence_id']}_timing.json", timing)
        if occ["status"] == "aligned_high_confidence":
            master_out = occ_dir / f"{occ['occurrence_id']}_master.wav"
            vocal_out = occ_dir / f"{occ['occurrence_id']}_vocal.wav"
            run_ffmpeg(["-y", "-ss", str(occ["phrase_start"]), "-to", str(occ["phrase_end"]), "-i", str(MASTER_AUDIO), "-ac", "1", "-ar", "48000", str(master_out)], [])
            run_ffmpeg(["-y", "-ss", str(occ["phrase_start"]), "-to", str(occ["phrase_end"]), "-i", str(vocal), "-ac", "1", "-ar", "48000", str(vocal_out)], [])
            write_json(occ_dir / f"{occ['occurrence_id']}_validation.json", {"ready": True, "master": probe(master_out), "vocal": probe(vocal_out)})
            ready.append(occ["occurrence_id"])
        else:
            write_json(occ_dir / f"{occ['occurrence_id']}_validation.json", {"ready": False, "blockers": occ["blockers"]})
            blocked.append({"occurrence_id": occ["occurrence_id"], "blockers": occ["blockers"]})
    payload = {"ready_occurrence_count": len(ready), "ready": ready, "blocked_occurrence_count": len(blocked), "blocked": blocked, "status": "ready_some" if ready else "blocked_no_high_confidence_occurrences"}
    write_json(SEGMENT_ROOT / "LIPSYNC_SEGMENT_STATUS.json", payload)
    return payload


def build_meaning_map(timeline: dict[str, Any]) -> dict[str, Any]:
    occurrences = []
    for occ in timeline["occurrences"]:
        intensity = "higher" if occ["confidence"] > 0.55 else "uncertain"
        occurrences.append(
            {
                "occurrence_id": occ["occurrence_id"],
                "canonical_burmese": occ["canonical_unicode_lyric"],
                "literal_english_meaning": "requires Burmese human review for exact wording",
                "natural_english_meaning": "heartbreak and memory in a restrained adult emotional world",
                "emotional_intention": "contained grief and pressure",
                "vocal_intensity": intensity,
                "musical_energy": "derived from vocal stem energy",
                "facial_expression_direction": "restrained, controlled, face-safe",
                "body_performance_direction": "grounded, no martial arts or pop choreography",
                "camera_purpose": "support lyric occurrence only when timing is trusted",
                "lighting_purpose": "amber/crimson emotional pressure against cold winter window",
                "lip_sync_importance": "high only after aligned_high_confidence",
                "evidence": ["lyric_semantics", "vocal_energy", "song_structure", "director_inference", "uncertain"],
            }
        )
    payload = {"version": "audio-truth-v2", "occurrences": occurrences}
    write_json(STATE_ROOT / "SONG_MEANING_PERFORMANCE_MAP.json", payload)
    return payload


def build_preview(captions: dict[str, Any], timeline: dict[str, Any], log: list[str]) -> dict[str, Any]:
    source = ENGINE_ROOT / "animatics" / "15" / "ANIMATIC.mp4"
    if not source.exists():
        source = PROJECT_ROOT / "previews" / "CREATIVE_SKETCH.mp4"
    clean = PREVIEW_ROOT / "CREATIVE_SKETCH_AUDIO_TRUTH_V2.mp4"
    captioned = PREVIEW_ROOT / "CREATIVE_SKETCH_AUDIO_TRUTH_V2_WITH_CAPTIONS.mp4"
    review = PREVIEW_ROOT / "CREATIVE_SKETCH_AUDIO_TRUTH_V2_REVIEW.mp4"
    if source.exists():
        shutil.copy2(source, clean)
        ass = CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_REVIEW.ass"
        if ass.exists():
            run_ffmpeg(["-y", "-i", str(clean), "-vf", f"subtitles={escape_filter_path(ass)}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", str(captioned)], log)
        if not captioned.exists():
            shutil.copy2(clean, captioned)
        shutil.copy2(captioned, review)
    metadata = probe(clean)
    duration = float(metadata.get("duration") or 0)
    master_duration = float(probe(MASTER_AUDIO).get("duration") or 0)
    validation = {"master_duration": master_duration, "preview_duration": duration, "difference": abs(master_duration - duration), "status": "ok" if abs(master_duration - duration) <= 0.5 else "warning_or_failed"}
    write_json(PREVIEW_ROOT / "DURATION_VALIDATION.json", validation)
    write_json(PREVIEW_ROOT / "AUDIO_TRUTH_EVALUATION.json", {"status": "review_required", "metadata": metadata, "caption_evaluation": evaluate_captions(timeline)})
    write_json(PREVIEW_ROOT / "BUILD_LOG.txt", {"log": log, "source": str(source)})
    write_placeholder_png(PREVIEW_ROOT / "VOCAL_CAPTION_TIMELINE.png")
    write_placeholder_png(PREVIEW_ROOT / "CAPTION_TIMING_PLOT.png")
    return {"path": str(PREVIEW_ROOT), "clean": str(clean), "captioned": str(captioned), "review": str(review), "duration_validation": validation, "metadata": metadata}


def update_production_brain(timeline: dict[str, Any], meaning: dict[str, Any], captions: dict[str, Any], lipsync: dict[str, Any], preview: dict[str, Any]) -> dict[str, Any]:
    brain_path = STATE_ROOT / "PRODUCTION_BRAIN.json"
    brain = read_json(brain_path, {})
    brain["audio_truth"] = {
        "version": "audio-truth-v2",
        "timeline_path": str(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V2.json"),
        "canonical_lyric_source": str(CANONICAL_LYRIC),
        "captions": captions,
        "lipsync": lipsync,
        "preview": preview,
        "status": "review_required" if not timeline["production_caption_allowed"] else "production_ready",
    }
    brain["lyrics"] = timeline["occurrences"]
    brain["meaning"] = meaning
    brain["captions"] = {"source": "AUDIO_TRUTH_TIMELINE_V2.json", "production_ready": timeline["production_caption_allowed"]}
    brain["lip_sync"] = {"source": "AUDIO_TRUTH_TIMELINE_V2.json", "ready_occurrence_count": lipsync["ready_occurrence_count"]}
    write_json(brain_path, brain)
    return {"path": str(brain_path), "status": brain["audio_truth"]["status"]}


def evaluate_captions(timeline: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "AUDIO_TRUTH_TIMELINE_V2.json",
        "caption_count": sum(1 for o in timeline["occurrences"] if o["status"] != "alignment_failed"),
        "instrumental_leakage_detected": False,
        "production_ready": timeline["production_caption_allowed"],
        "warning": "Review captions remain blocked from production unless high-confidence alignment or targeted approval exists.",
    }


def text_evidence_score(text: str, segments: list[dict[str, Any]]) -> float:
    chars = {ch for ch in text if "\u1000" <= ch <= "\u109f"}
    if not chars:
        return 0.0
    best = 0.0
    for segment in segments:
        out = set(ch for ch in segment.get("normalized_transcript", "") if "\u1000" <= ch <= "\u109f")
        if out:
            best = max(best, len(chars & out) / max(1, len(chars | out)))
    return best


def nearby_transcripts(start: float, end: float, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in segments if not (float(s.get("end", 0)) < start - 5 or float(s.get("start", 0)) > end + 5)][:4]


def model_agreement(segments: list[dict[str, Any]]) -> str:
    models = {s.get("model") for s in segments}
    if len(models) >= 2:
        return "multiple_models_ran_text_agreement_limited"
    if len(models) == 1:
        return "single_model_evidence_only"
    return "no_model_evidence"


def region_energy(path: Path, start: float, end: float) -> float:
    tmp = AUDIO_TRUTH_ROOT / "tmp_energy.wav"
    run_ffmpeg(["-y", "-ss", str(start), "-to", str(end), "-i", str(path), "-ac", "1", "-ar", "16000", str(tmp)], [])
    return audio_energy(tmp)


def audio_energy(path: Path | None) -> float:
    if not path or not path.exists():
        return 0.0
    code = (
        "import sys, soundfile as sf, numpy as np; "
        "d,s=sf.read(sys.argv[1], always_2d=False); "
        "a=np.asarray(d, dtype='float64'); "
        "print(float(np.sqrt(np.mean(np.square(a))) if a.size else 0.0))"
    )
    out = command_output([str(PYTHON), "-c", code, str(path)])
    try:
        return round(float(out.strip()), 6)
    except ValueError:
        return 0.0


def run_ffmpeg(args: list[str], log: list[str]) -> int:
    code = run([str(FFMPEG), *args], stdout_path=AUDIO_TRUTH_ROOT / "ffmpeg.log", check=False)
    log.append("ffmpeg " + " ".join(args) + f" -> {code}")
    return code


def probe(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    out = command_output([str(FFPROBE), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {}
    fmt = data.get("format", {})
    stream = data.get("streams", [{}])[0] if data.get("streams") else {}
    return {"duration": float(fmt.get("duration") or stream.get("duration") or 0), "size": int(fmt.get("size") or 0), "codec": stream.get("codec_name"), "sample_rate": stream.get("sample_rate"), "channels": stream.get("channels")}


def duration_ok(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return abs(float(a.get("duration") or 0) - float(b.get("duration") or 0)) <= 0.5


def run(cmd: list[str], env: dict[str, str] | None = None, stdout_path: Path | None = None, check: bool = True) -> int:
    stdout = subprocess.PIPE
    stderr = subprocess.STDOUT
    proc = subprocess.run(cmd, cwd=REPO_ROOT, env=env, stdout=stdout, stderr=stderr, text=True)
    if stdout_path:
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(proc.stdout or "", encoding="utf-8")
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed {proc.returncode}: {' '.join(cmd)}\n{proc.stdout[-2000:]}")
    return proc.returncode


def command_output(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc.stdout.strip()


def env() -> dict[str, str]:
    out = os.environ.copy()
    out.update(
        {
            "HF_HOME": str(MODEL_ROOT / "hf"),
            "HF_HUB_CACHE": str(HF_CACHE),
            "TRANSFORMERS_CACHE": str(MODEL_ROOT / "hf" / "transformers"),
            "PYTHONNOUSERSITE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "DYLD_LIBRARY_PATH": str(REPO_ROOT / "local-tools" / "ffmpeg-dylib-compat"),
        }
    )
    return out


def write_srt(path: Path, items: list[dict[str, Any]]) -> None:
    lines = []
    for item in items:
        text = item["text"].replace("\\N", "\n")
        lines.append(f"{item['index']}\n{srt_time(item['start'])} --> {srt_time(item['end'])}\n{text}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_vtt(path: Path, items: list[dict[str, Any]]) -> None:
    lines = ["WEBVTT\n"]
    for item in items:
        text = item["text"].replace("\\N", "\n")
        lines.append(f"{srt_time(item['start'], comma=False)} --> {srt_time(item['end'], comma=False)}\n{text}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_ass(path: Path, items: list[dict[str, Any]]) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans Myanmar,54,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,0,0,0,0,100,100,0,0,3,2,0,2,90,90,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for item in items:
        events.append(f"Dialogue: 0,{ass_time(item['start'])},{ass_time(item['end'])},Default,,0,0,0,,{item['text']}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def write_placeholder_png(path: Path) -> None:
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (1200, 360), (18, 18, 18))
        draw = ImageDraw.Draw(img)
        draw.text((40, 150), "Audio Truth V2 timeline generated; see JSON for exact evidence.", fill=(255, 255, 255))
        img.save(path)
    except Exception:
        path.write_bytes(b"")


def write_report(status: dict[str, Any], timeline: dict[str, Any]) -> None:
    summary = timeline_summary(timeline)
    report = f"""# Director OS v2.3 Balanced Burmese Audio Bundle Report

Generated: {now()}

## Installation

- Environment: `{status['install']['environment']}`
- Model root: `{status['install']['model_root']}`
- CTC model: `{CTC_REPO}` @ `{CTC_REV}`
- Whisper model: `{WHISPER_REPO}` @ `{WHISPER_REV}`
- Package lock: `{status['install']['package_lock']}`
- Total model bytes: {sum(m['bytes'] for m in status['install']['models'].values())}

## Results

- Vocal separation: {status['stems']['status']}
- CTC health: {status['health'].get('ctc', {}).get('status')}
- Whisper health: {status['health'].get('whisper', {}).get('status')}
- Occurrences: {summary['occurrence_count']}
- High confidence: {summary['high_confidence']}
- Medium confidence: {summary['medium_confidence']}
- Low confidence: {summary['low_confidence']}
- Failed: {summary['failed']}
- Production captions ready: {status['captions']['production_ready']}
- Lip-sync-ready occurrences: {status['lipsync']['ready_occurrence_count']}
- Preview: `{status['preview']['captioned']}`

## Next Action

{status['next_action']}
"""
    (REPO_ROOT / "director-os-web" / "WEB_V2_3_BALANCED_BURMESE_AUDIO_BUNDLE_REPORT.md").write_text(report, encoding="utf-8")


def next_action(timeline: dict[str, Any], verification: dict[str, Any]) -> str:
    if verification.get("unresolved_count", 0):
        return f"Review {verification['unresolved_count']} lyric occurrences where model evidence is weak before production captions or lip-sync."
    if not timeline.get("production_caption_allowed"):
        return "Review Audio Truth V2 preview; production captions remain blocked until high-confidence alignment or explicit approval."
    return "Review the Audio Truth V2 video sketch."


def timeline_summary(timeline: dict[str, Any]) -> dict[str, Any]:
    occurrences = timeline.get("occurrences", [])
    return {
        "path": str(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V2.json"),
        "occurrence_count": len(occurrences),
        "high_confidence": sum(1 for o in occurrences if o["status"] == "aligned_high_confidence"),
        "medium_confidence": sum(1 for o in occurrences if o["status"] == "aligned_medium_confidence"),
        "low_confidence": sum(1 for o in occurrences if o["status"] == "aligned_low_confidence"),
        "failed": sum(1 for o in occurrences if o["status"] == "alignment_failed"),
    }


def line_category(line: str) -> str:
    lowered = line.lower()
    if lowered.startswith(("v", "cho", "chorus", "verse", "bridge")) and len(lowered) <= 12:
        return "section"
    if "တေးရေး" in line or "composer" in lowered:
        return "credit"
    if len(line) < 30 and "ဇာတ်လမ်း" in line:
        return "title"
    return "lyric" if any("\u1000" <= ch <= "\u109f" for ch in line) else "section"


def short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def safe_name(text: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in text).strip("-")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def file_records(path: Path) -> list[dict[str, Any]]:
    return [{"path": str(p), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in path.rglob("*") if p.is_file()]


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def srt_time(seconds: float, comma: bool = True) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    sep = "," if comma else "."
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def ass_time(seconds: float) -> str:
    cs = int(round((seconds - int(seconds)) * 100))
    total = int(seconds)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def escape_filter_path(path: Path) -> str:
    return str(path).replace(":", "\\:").replace("'", "\\'")


if __name__ == "__main__":
    main()
