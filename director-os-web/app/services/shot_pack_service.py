from __future__ import annotations

from pathlib import Path

from app.config import ENGINE_ROOT
from app.services.engine_reader import read_text, relative


SHOT_PACK_ROOT = ENGINE_ROOT / "shot-packs"


def list_shot_packs() -> list[dict[str, str]]:
    packs: list[dict[str, str]] = []
    if not SHOT_PACK_ROOT.exists():
        return packs
    for path in sorted(p for p in SHOT_PACK_ROOT.iterdir() if p.is_dir()):
        intent_path = path / "SHOT_INTENT.md"
        first_line = "UNKNOWN"
        for line in read_text(intent_path).splitlines():
            if line.startswith("Purpose:"):
                first_line = line.replace("Purpose:", "").strip()
                break
        packs.append({"id": path.name, "path": relative(path), "purpose": first_line})
    return packs


def get_shot_pack(shot_id: str) -> dict[str, object]:
    path = SHOT_PACK_ROOT / shot_id
    files = []
    if path.exists():
        for file_path in sorted(path.iterdir()):
            if file_path.is_file():
                files.append(
                    {
                        "name": file_path.name,
                        "path": relative(file_path),
                        "content": read_text(file_path, 6000),
                    }
                )
    return {"id": shot_id, "path": relative(path), "files": files}
