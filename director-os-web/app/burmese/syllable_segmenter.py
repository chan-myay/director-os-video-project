from __future__ import annotations


BREAK_CHARS = set(" ၊။,.!?;:\n\t")


def segment_syllables(text: str) -> list[str]:
    parts: list[str] = []
    current = ""
    for char in text:
        current += char
        if char in BREAK_CHARS:
            if current.strip():
                parts.append(current.strip())
            current = ""
    if current.strip():
        parts.append(current.strip())
    return parts
