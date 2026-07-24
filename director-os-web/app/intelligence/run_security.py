from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ProcessResult:
    stdout: str
    stderr: str
    exit_status: int
    started_at: float
    ended_at: float
    timed_out: bool = False


def ensure_workspace(path: str | Path, allowed_root: str | Path) -> Path:
    root = Path(allowed_root).expanduser().resolve()
    workspace = Path(path).expanduser().resolve()
    if workspace != root and root not in workspace.parents:
        raise ValueError(f"Workspace {workspace} is outside allowed root {root}")
    return workspace


def run_process(args: list[str], cwd: Path, timeout: int, stdin: Optional[str] = None) -> ProcessResult:
    started = time.time()
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        ended = time.time()
        return ProcessResult(as_text(completed.stdout), as_text(completed.stderr), completed.returncode, started, ended, False)
    except subprocess.TimeoutExpired as exc:
        ended = time.time()
        return ProcessResult(as_text(exc.stdout), as_text(exc.stderr), 124, started, ended, True)


def as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
