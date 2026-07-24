from __future__ import annotations

from app.burmese.normalization_service import normalize_burmese


def pronunciation_helper(text: str, overrides: dict[str, str] | None = None) -> str:
    normalized = normalize_burmese(text)
    overrides = overrides or {}
    for original, replacement in overrides.items():
        normalized = normalized.replace(original, replacement)
    return normalized
