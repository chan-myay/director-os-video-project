from __future__ import annotations


ZAWGYI_HINTS = set("ၐၑၒၓၔၕၚၛၜၝၞၟ")


def detect_encoding(text: str) -> dict:
    if not text.strip():
        return {"encoding": "unknown", "zawgyi_probability": 0.0, "confidence": 0.0}
    zawgyi_hits = sum(1 for char in text if char in ZAWGYI_HINTS)
    kinzi_like = text.count("ၤ") + text.count("ႋ") + text.count("ႌ")
    probability = min(1.0, (zawgyi_hits + kinzi_like) / max(1, len(text) / 12))
    encoding = "zawgyi" if probability > 0.55 else "unicode"
    if 0.35 <= probability <= 0.55:
        encoding = "uncertain"
    return {"encoding": encoding, "zawgyi_probability": round(probability, 3), "confidence": round(abs(probability - 0.5) * 2, 3)}
