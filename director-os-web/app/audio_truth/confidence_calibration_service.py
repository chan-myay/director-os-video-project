from __future__ import annotations

from typing import Any


def calibrate_occurrence(evidence: dict[str, Any]) -> dict[str, Any]:
    ctc = float(evidence.get("ctc_alignment_score") or 0)
    token_coverage = float(evidence.get("ctc_token_coverage") or 0)
    order = float(evidence.get("phrase_order_score") or 0)
    energy = float(evidence.get("stem_vocal_energy_score") or 0)
    monotonic = 1.0 if evidence.get("monotonic_path_valid") else 0.0
    no_overlap = 1.0 if not evidence.get("neighbouring_phrase_overlap") else 0.0
    repeated = float(evidence.get("repeated_occurrence_score") or 0)
    whisper = float(evidence.get("whisper_text_similarity") or 0)
    instrumental_clean = 1.0 if not evidence.get("instrumental_contamination") else 0.0

    score = (
        ctc * 0.28
        + token_coverage * 0.16
        + order * 0.14
        + energy * 0.12
        + monotonic * 0.12
        + no_overlap * 0.07
        + repeated * 0.05
        + whisper * 0.03
        + instrumental_clean * 0.03
    )
    blockers: list[str] = []
    contradicting: list[str] = []
    supporting: list[str] = []
    if token_coverage < 0.98:
        blockers.append("TOKENIZER_COVERAGE_INCOMPLETE")
    else:
        supporting.append("tokenizer_coverage_complete")
    if not monotonic:
        blockers.append("FULL_SONG_PATH_NOT_MONOTONIC")
    else:
        supporting.append("monotonic_full_song_path")
    if evidence.get("neighbouring_phrase_overlap"):
        blockers.append("NEIGHBOURING_PHRASE_OVERLAP")
        contradicting.append("overlaps_neighbour")
    if evidence.get("instrumental_contamination"):
        blockers.append("INSTRUMENTAL_CONFLICT")
        contradicting.append("instrumental_conflict")
    if ctc >= 0.62:
        supporting.append("ctc_text_evidence_strong")
    elif ctc >= 0.5:
        supporting.append("ctc_text_evidence_usable")
    else:
        contradicting.append("ctc_text_evidence_weak")
    if whisper >= 0.25:
        supporting.append("whisper_supports_region")
    elif whisper == 0:
        contradicting.append("whisper_timing_or_text_missing")

    if blockers:
        confidence_class = "blocked" if "FULL_SONG_PATH_NOT_MONOTONIC" in blockers else "low"
    elif score >= 0.72 and ctc >= 0.62 and energy >= 0.45:
        confidence_class = "high"
    elif score >= 0.55:
        confidence_class = "medium"
    else:
        confidence_class = "low"

    return {
        "confidence_score": round(score, 3),
        "confidence_class": confidence_class,
        "supporting_evidence": supporting,
        "contradicting_evidence": contradicting,
        "blocker_reason": blockers,
        "promotion_reason": supporting if confidence_class == "high" else [],
    }
