from __future__ import annotations


def caption_safe_lines(text: str, max_chars: int = 34) -> list[str]:
    words = text.split()
    if not words:
        return [text] if text else []
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
