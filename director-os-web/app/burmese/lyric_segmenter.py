from __future__ import annotations


def segment_lyrics(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]
