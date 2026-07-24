from __future__ import annotations

from pathlib import Path

from app.config import REFERENCE_ROOT
from app.services.engine_reader import read_text, relative


def reference_status() -> dict[str, object]:
    files = []
    if REFERENCE_ROOT.exists():
        for path in sorted(REFERENCE_ROOT.rglob("*")):
            if path.is_file():
                files.append({"name": path.name, "path": relative(path), "preview": read_text(path, 1200)})
    return {
        "root": relative(REFERENCE_ROOT),
        "policy": "Store URLs, notes, tags, and analysis. Do not rehost copyrighted media.",
        "files": files,
    }
