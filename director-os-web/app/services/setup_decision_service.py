from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.config import REPO_ROOT
from app.services.audit_service import write_audit
from app.services.db import connect, initialize_database
from app.system_tools.tool_health import system_tool_health


def storyboard_model_decision_context() -> dict[str, Any]:
    total, used, free = shutil.disk_usage(str(REPO_ROOT))
    return {
        "hardware": {
            "machine": platform.machine(),
            "platform": platform.platform(),
            "free_disk_gb": free // (1024**3),
            "unified_memory": "UNKNOWN from stdlib; verify in System Settings before model install",
        },
        "existing_comfyui": (REPO_ROOT / "local-tools/research-repos/ComfyUI").exists(),
        "primary": {
            "name": "ComfyUI local storyboard workflow with a lightweight SDXL/Lightning-class checkpoint",
            "official_source": "ComfyUI upstream plus separately approved model source",
            "license": "runtime GPL; model license must be reviewed before download",
            "download_size": "model-dependent, typically multiple GB",
            "expected_disk": "10-25 GB including cache/workflows",
            "memory": "best with 16GB+ unified memory; final choice requires hardware confirmation",
            "commands": "not generated until approval",
            "privacy": "local, no cloud upload",
        },
        "fallback": {
            "name": "Continue with existing asset composite previs",
            "download_size": "0",
            "expected_disk": "already present",
            "privacy": "local",
        },
        "cloud": {
            "name": "Approved cloud image backend",
            "requires": "explicit media upload approval and spend limit",
            "privacy": "high risk if personal references are uploaded",
        },
    }


def burmese_voice_decision_context() -> dict[str, Any]:
    system_voices = []
    say = shutil.which("say")
    if say:
        try:
            result = subprocess.run([say, "-v", "?"], capture_output=True, text=True, timeout=10, check=False)
            system_voices = [line for line in result.stdout.splitlines() if "Burmese" in line or "Myanmar" in line or "my_" in line]
        except Exception:
            system_voices = []
    return {
        "system_voice_available": bool(say),
        "burmese_system_voices": system_voices,
        "azure_configured": False,
        "local_voice_runtime": False,
        "primary": {
            "name": "Caption-only for now",
            "privacy": "local/no voice upload",
            "quality": "no generated voice",
            "blocks_director_run": False,
        },
        "fallback": {
            "name": "Manual human voice workflow",
            "privacy": "user-controlled",
            "consent_required": True,
        },
    }


def record_setup_decision(decision_type: str, choice: str, notes: str = "") -> None:
    initialize_database()
    with connect() as conn:
        conn.execute(
            "INSERT INTO setup_decisions (decision_type, choice, notes) VALUES (?, ?, ?)",
            (decision_type, choice, notes),
        )
    write_audit("setup_decision", "setup_decisions", decision_type, f"Setup decision recorded: {choice}", {"notes": notes})


def list_setup_decisions() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM setup_decisions ORDER BY decision_id DESC").fetchall()
    return [dict(row) for row in rows]


def system_tools_context() -> dict[str, Any]:
    return system_tool_health()
