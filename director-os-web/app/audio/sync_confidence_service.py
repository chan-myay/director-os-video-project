from __future__ import annotations


def confidence_for_boundary(duration: float, gap_before: float, gap_after: float) -> tuple[float, str, bool]:
    confidence = 0.55
    reasons = ["existing vocal phrase boundary", "lyric phrase order"]
    if duration < 0.8:
        confidence -= 0.15
        reasons.append("very short phrase")
    if duration > 14:
        confidence -= 0.1
        reasons.append("long phrase may contain multiple sung lines")
    if gap_before >= 0.25 or gap_after >= 0.25:
        confidence += 0.05
        reasons.append("nearby instrumental/low-vocal gap")
    confidence = max(0.1, min(0.72, confidence))
    return confidence, "; ".join(reasons), confidence < 0.7
