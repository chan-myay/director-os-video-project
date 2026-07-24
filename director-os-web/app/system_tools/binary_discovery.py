from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from app.config import REPO_ROOT


def candidate_paths(name: str) -> list[str]:
    env_name = f"DIRECTOR_OS_{name.upper()}"
    candidates = [
        os.environ.get(env_name, ""),
        shutil.which(name) or "",
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/usr/bin/{name}",
        str(REPO_ROOT / "local-tools" / "envs" / "faceswap" / "bin" / name),
        str(REPO_ROOT / "local-tools" / "envs" / "facefusion" / "bin" / name),
        str(REPO_ROOT / "local-tools" / "envs" / "faceswap" / "lib" / "python3.13" / "site-packages" / "ffmpeg" / "binaries" / name),
    ]
    return [candidate for candidate in candidates if candidate]


def discover_binary(name: str) -> Optional[str]:
    for candidate in candidate_paths(name):
        path = Path(candidate).expanduser()
        if path.exists() and path.is_file():
            if verify_binary(str(path)):
                return str(path)
    return None


def verify_binary(path: str) -> bool:
    try:
        result = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10, check=False)
    except Exception:
        return False
    return result.returncode == 0


def binary_version(path: Optional[str]) -> str:
    if not path:
        return ""
    try:
        result = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10, check=False)
    except Exception as exc:
        return f"error: {type(exc).__name__}"
    if result.returncode != 0:
        return (result.stderr or "version check failed").strip().splitlines()[0]
    return (result.stdout or "").strip().splitlines()[0]
