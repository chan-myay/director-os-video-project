from __future__ import annotations

import unicodedata


def normalize_burmese(text: str) -> str:
    return unicodedata.normalize("NFC", text.strip())
