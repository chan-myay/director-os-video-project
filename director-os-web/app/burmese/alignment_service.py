from __future__ import annotations


def rough_line_timing(lines: list[str], duration: float) -> list[dict]:
    if not lines:
        return []
    step = duration / len(lines)
    return [{"line": line, "start": round(i * step, 3), "end": round((i + 1) * step, 3)} for i, line in enumerate(lines)]
