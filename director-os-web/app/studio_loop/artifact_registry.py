from __future__ import annotations

from pathlib import Path
from typing import Any


def artifact(path: Path, artifact_type: str, origin: str = "local") -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "path": str(path),
        "exists": path.exists(),
        "origin": origin,
        "status": "created" if path.exists() else "missing",
    }
