from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import ENGINE_ROOT, REPO_ROOT


STATE_PATH = ENGINE_ROOT / "state" / "STUDIO_LOOP_STATE.json"
BRAIN_PATH = ENGINE_ROOT / "state" / "PRODUCTION_BRAIN.json"
EVAL_ROOT = ENGINE_ROOT / "evaluations"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default or {}


def loop_eval_dir(loop_id: int) -> Path:
    path = EVAL_ROOT / str(loop_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_loop_state(data: dict[str, Any]) -> None:
    write_json(STATE_PATH, data)


def write_production_brain(data: dict[str, Any]) -> None:
    write_json(BRAIN_PATH, data)
