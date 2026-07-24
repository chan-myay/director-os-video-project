from __future__ import annotations

from app.burmese.encoding_detector import detect_encoding


DETECTOR_NAME = "director_os_myanmar_tools_compatible_detector"
DETECTOR_VERSION = "1.0.3-local-heuristic"


def detect_myanmar_encoding(text: str) -> dict:
    detected = detect_encoding(text)
    return {
        "detector": DETECTOR_NAME,
        "detector_version": DETECTOR_VERSION,
        "encoding": detected["encoding"],
        "confidence": detected["confidence"],
        "zawgyi_probability": detected["zawgyi_probability"],
    }
