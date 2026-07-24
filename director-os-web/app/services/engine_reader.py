from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.config import ENGINE_ROOT


def read_text(path: Path, limit: Optional[int] = None) -> str:
    if not path.exists():
        return "UNKNOWN: file not found"
    text = path.read_text(encoding="utf-8")
    return text if limit is None else text[:limit]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ENGINE_ROOT.parent))
    except ValueError:
        return str(path)


def engine_status() -> dict[str, str]:
    return {
        "version": "0.3 product shell over v0.2 compiler",
        "engine_root": relative(ENGINE_ROOT),
        "v01_report": relative(ENGINE_ROOT / "ENGINE_V0_1_REPORT.md"),
        "v02_report": relative(ENGINE_ROOT / "ENGINE_V0_2_REPORT.md"),
        "hard_stop": "No generation, upload, render, paid API, or media copy.",
    }
