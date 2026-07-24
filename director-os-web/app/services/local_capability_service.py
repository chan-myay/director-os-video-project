from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from app.config import ENGINE_ROOT, REPO_ROOT
from app.services.db import connect, initialize_database
from app.system_tools.tool_health import system_tool_health


STATE_ROOT = ENGINE_ROOT / "state"


def run_local_capability_audit() -> dict[str, Any]:
    initialize_database()
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    hardware = detect_hardware()
    toolchain = detect_toolchain()
    models = detect_local_models()
    benchmarks = run_deterministic_benchmarks(toolchain, hardware)
    matrix = build_capability_matrix(hardware, toolchain, models, benchmarks)
    write_state("LOCAL_HARDWARE.json", hardware)
    write_state("LOCAL_TOOLCHAIN.json", toolchain)
    write_state("LOCAL_MODEL_REGISTRY.json", models)
    write_state("LOCAL_BENCHMARKS.json", benchmarks)
    write_state("LOCAL_CAPABILITY_MATRIX.json", matrix)
    persist_capabilities(matrix, models, benchmarks)
    return {
        "hardware": hardware,
        "toolchain": toolchain,
        "models": models,
        "benchmarks": benchmarks,
        "matrix": matrix,
    }


def local_capability_summary(refresh: bool = False) -> dict[str, Any]:
    if refresh or not (STATE_ROOT / "LOCAL_CAPABILITY_MATRIX.json").exists():
        return run_local_capability_audit()
    return {
        "hardware": read_state("LOCAL_HARDWARE.json"),
        "toolchain": read_state("LOCAL_TOOLCHAIN.json"),
        "models": read_state("LOCAL_MODEL_REGISTRY.json"),
        "benchmarks": read_state("LOCAL_BENCHMARKS.json"),
        "matrix": read_state("LOCAL_CAPABILITY_MATRIX.json"),
    }


def detect_hardware() -> dict[str, Any]:
    total, _used, free = shutil.disk_usage(str(REPO_ROOT))
    return {
        "machine": platform.machine(),
        "architecture": platform.platform(),
        "macos_version": platform.mac_ver()[0],
        "chip_model": sysctl("machdep.cpu.brand_string") or "UNKNOWN",
        "cpu_core_count": os.cpu_count() or 0,
        "gpu_core_count": "UNKNOWN",
        "unified_memory_bytes": safe_int(sysctl("hw.memsize")),
        "memory_pressure": command_text(["/usr/bin/memory_pressure", "-Q"], 5),
        "free_disk_bytes": free,
        "total_disk_bytes": total,
    }


def detect_toolchain() -> dict[str, Any]:
    tools = system_tool_health()
    python_versions = {
        "python3": binary_version(shutil.which("python3")),
        "active": platform.python_version(),
    }
    return {
        "python": python_versions,
        "homebrew": {"path": shutil.which("brew") or "", "version": binary_version(shutil.which("brew"))},
        "xcode_select": command_text(["xcode-select", "-p"], 5),
        "swift": {"path": shutil.which("swift") or "", "version": binary_version(shutil.which("swift"))},
        "ffmpeg": tools["ffmpeg"],
        "ffprobe": tools["ffprobe"],
        "metal": {"classification": "local", "status": "available_on_apple_silicon" if platform.machine() == "arm64" else "unknown"},
        "mps": module_status("torch"),
        "mlx": module_status("mlx"),
        "coremltools": module_status("coremltools"),
        "opencv": module_status("cv2"),
        "pyscenedetect": module_status("scenedetect"),
        "opentimelineio": module_status("opentimelineio"),
        "ml_for_audio": {
            "mlx_whisper": shutil.which("mlx_whisper") or str(REPO_ROOT / "local-tools/envs/facefusion/bin/mlx_whisper"),
        },
        "comfyui_code": (REPO_ROOT / "local-tools/research-repos/ComfyUI").exists() or (REPO_ROOT / "local-tools/ComfyUI").exists(),
    }


def detect_local_models() -> dict[str, Any]:
    candidates = []
    roots = [
        REPO_ROOT / "local-tools",
        REPO_ROOT / "models",
        REPO_ROOT / "face-correction" / "work" / "models",
    ]
    patterns = ["*.safetensors", "*.ckpt", "*.gguf", "*.mlmodel*", "*.pth", "*.onnx", "*.pt"]
    for root in roots:
        if not root.exists():
            continue
        for pattern in patterns:
            for path in root.rglob(pattern):
                if path.is_file():
                    candidates.append(model_record(path))
    return {
        "installed_model_count": len(candidates),
        "models": candidates[:250],
        "scan_roots": [str(root) for root in roots],
        "note": "Registry records local files only; no model was downloaded during this audit.",
    }


def run_deterministic_benchmarks(toolchain: dict[str, Any], hardware: dict[str, Any]) -> dict[str, Any]:
    result_dir = ENGINE_ROOT / "benchmarks" / "local"
    result_dir.mkdir(parents=True, exist_ok=True)
    start = time.time()
    ffmpeg = toolchain.get("ffmpeg", {}).get("path", "")
    output = result_dir / "ffmpeg_test_frame.png"
    success = False
    elapsed = 0.0
    if ffmpeg:
        completed = subprocess.run(
            [ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=1:duration=1", "-frames:v", "1", str(output)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
            check=False,
        )
        elapsed = time.time() - start
        success = completed.returncode == 0 and output.exists()
    benchmark = {
        "model": "none",
        "runtime": "ffmpeg_deterministic",
        "hardware": hardware.get("chip_model", "UNKNOWN"),
        "startup_time": 0,
        "processing_time": elapsed,
        "peak_memory": "not_measured",
        "dimensions": "320x180",
        "result_path": str(output) if success else "",
        "success": success,
        "quality_review_state": "tool_health_only",
    }
    return {"benchmarks": [benchmark]}


def build_capability_matrix(
    hardware: dict[str, Any], toolchain: dict[str, Any], models: dict[str, Any], benchmarks: dict[str, Any]
) -> dict[str, Any]:
    return {
        "execution_policy": {
            "level_1_local_deterministic": "preferred",
            "level_2_apple_silicon_local_ai": "available_after_model_install_or_runtime_detection",
            "level_3_trusted_local_model_servers": "not_configured",
            "level_4_private_remote_gpu": "private_remote_option",
            "level_5_commercial_cloud": "cloud_optional_requires_approval",
        },
        "capabilities": [
            capability("mp4_animatic", "local", toolchain["ffmpeg"]["found"] and toolchain["ffprobe"]["found"]),
            capability("caption_export", "local", True),
            capability("local_audio_metadata", "local", toolchain["ffprobe"]["found"]),
            capability("local_storyboard_ai", "local_after_install", False),
            capability("burmese_voice_generation", "local_after_install", False),
            capability("infinitetalk_local", "local_after_install", False),
            capability("infinitetalk_runpod", "private_remote_option", False),
            capability("final_video_generation_local", "local_experimental", False),
            capability("composite_previs", "local", True),
            capability("result_qc", "local", True),
        ],
        "hardware_summary": hardware,
        "model_count": models.get("installed_model_count", 0),
        "benchmarks": benchmarks.get("benchmarks", []),
    }


def persist_capabilities(matrix: dict[str, Any], models: dict[str, Any], benchmarks: dict[str, Any]) -> None:
    initialize_database()
    with connect() as conn:
        for item in matrix.get("capabilities", []):
            conn.execute(
                """
                INSERT INTO local_capability_records
                    (capability_type, name, status, classification, details, health, last_checked)
                VALUES ('capability', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(capability_type, name) DO UPDATE SET
                    status = excluded.status,
                    classification = excluded.classification,
                    details = excluded.details,
                    health = excluded.health,
                    last_checked = CURRENT_TIMESTAMP
                """,
                (
                    item["name"],
                    item["status"],
                    item["classification"],
                    json.dumps(item, ensure_ascii=False),
                    json.dumps({"operational": item["operational"]}),
                ),
            )
        for model in models.get("models", [])[:250]:
            conn.execute(
                """
                INSERT INTO local_model_records
                    (name, source, local_path, version_or_commit, code_license, model_license,
                     commercial_use_state, file_size, model_family, supported_tasks, runtime,
                     health, last_benchmark, privacy, approval_state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model["name"],
                    model["source"],
                    model["local_path"],
                    model["version_or_commit"],
                    model["code_license"],
                    model["model_license"],
                    model["commercial_use_state"],
                    model["file_size"],
                    model["model_family"],
                    model["supported_tasks"],
                    model["runtime"],
                    model["health"],
                    model["last_benchmark"],
                    model["privacy"],
                    model["approval_state"],
                ),
            )
        for bench in benchmarks.get("benchmarks", []):
            conn.execute(
                """
                INSERT INTO local_benchmarks
                    (model, runtime, hardware, startup_time, processing_time, peak_memory,
                     dimensions, result_path, success, quality_review_state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bench["model"],
                    bench["runtime"],
                    bench["hardware"],
                    bench["startup_time"],
                    bench["processing_time"],
                    bench["peak_memory"],
                    bench["dimensions"],
                    bench["result_path"],
                    1 if bench["success"] else 0,
                    bench["quality_review_state"],
                ),
            )


def capability(name: str, classification: str, operational: bool) -> dict[str, Any]:
    return {
        "name": name,
        "classification": classification,
        "operational": operational,
        "status": "operational" if operational else classification,
    }


def model_record(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    family = {
        ".gguf": "llm_or_speech",
        ".safetensors": "diffusion_or_adapter",
        ".ckpt": "checkpoint",
        ".onnx": "onnx",
        ".pth": "torch",
        ".pt": "torch",
    }.get(suffix, "unknown")
    return {
        "name": path.name,
        "source": "local_scan",
        "local_path": str(path),
        "version_or_commit": "UNKNOWN",
        "code_license": "UNKNOWN",
        "model_license": "UNKNOWN",
        "commercial_use_state": "UNKNOWN",
        "file_size": path.stat().st_size,
        "model_family": family,
        "supported_tasks": "UNKNOWN",
        "runtime": "UNKNOWN",
        "health": "found_not_benchmarked",
        "last_benchmark": "",
        "privacy": "local",
        "approval_state": "existing_local_file_not_approved_for_new_use",
    }


def module_status(module: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["python3", "-c", f"import {module}; print(getattr({module}, '__version__', 'installed'))"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
        return {
            "available": result.returncode == 0,
            "version": result.stdout.strip() if result.returncode == 0 else "",
            "error": result.stderr.strip()[:300] if result.returncode else "",
        }
    except Exception as exc:
        return {"available": False, "version": "", "error": str(exc)}


def sysctl(key: str) -> str:
    return command_text(["sysctl", "-n", key], 5).strip()


def safe_int(value: str) -> int:
    try:
        return int(value.strip())
    except Exception:
        return 0


def binary_version(path: str | None) -> str:
    if not path:
        return ""
    command = [path, "--version"] if Path(path).name != "swift" else [path, "--version"]
    text = command_text(command, 8)
    return text.splitlines()[0] if text else ""


def command_text(args: list[str], timeout: int) -> str:
    try:
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)
        return (result.stdout or result.stderr or "").strip()
    except Exception:
        return ""


def write_state(name: str, data: dict[str, Any]) -> None:
    (STATE_ROOT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_state(name: str) -> dict[str, Any]:
    path = STATE_ROOT / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
