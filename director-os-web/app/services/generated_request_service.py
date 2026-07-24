from __future__ import annotations

from app.config import ENGINE_ROOT
from app.services.engine_reader import read_text, relative


GENERATED_ROOT = ENGINE_ROOT / "generated-requests"


def list_generated_requests() -> list[dict[str, object]]:
    packages: list[dict[str, object]] = []
    if not GENERATED_ROOT.exists():
        return packages
    for package_dir in sorted(p for p in GENERATED_ROOT.iterdir() if p.is_dir()):
        files = sorted(file_path.name for file_path in package_dir.iterdir() if file_path.is_file())
        packages.append({"id": package_dir.name, "path": relative(package_dir), "files": files})
    return packages


def get_generated_file(shot_id: str, filename: str) -> dict[str, str]:
    path = GENERATED_ROOT / shot_id / filename
    return {"shot_id": shot_id, "filename": filename, "path": relative(path), "content": read_text(path)}
