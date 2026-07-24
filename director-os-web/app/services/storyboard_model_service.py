from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from app.config import REPO_ROOT
from app.services.audit_service import write_audit
from app.services.db import connect, initialize_database
from app.services.director_workspace_service import get_storyboard_card, raw_png, write_exports


STATE_ROOT = REPO_ROOT / "director-os" / "state"
LOCAL_GENERATION_ROOT = Path(
    os.environ.get(
        "DIRECTOR_OS_STORYBOARD_MODEL_ROOT",
        str(REPO_ROOT / "director-os" / "local-generation" / "storyboard-model"),
    )
)
STORYBOARD_VARIANT_ROOT = Path(
    os.environ.get(
        "DIRECTOR_OS_STORYBOARD_VARIANT_ROOT",
        str(REPO_ROOT / "director-os" / "storyboard-ai-variants"),
    )
)

PRIMARY_COMMIT = "97ac5e6280e8c65e48a609722229eb9d03ef2cbe"
FALLBACK_COMMIT = "e12202c1f6405b83918b58a5d097cd61e3e1f702"


def storyboard_model_decision_context() -> dict[str, Any]:
    initialize_database()
    hardware = _read_json(STATE_ROOT / "LOCAL_HARDWARE.json")
    toolchain = _read_json(STATE_ROOT / "LOCAL_TOOLCHAIN.json")
    registry = _read_json(STATE_ROOT / "LOCAL_MODEL_REGISTRY.json")
    decisions = _storyboard_decisions()
    installations = _installations()
    benchmarks = _benchmarks()
    variants = _variants()
    return {
        "hardware": {
            "chip": hardware.get("apple_chip", "UNKNOWN"),
            "architecture": hardware.get("architecture", "UNKNOWN"),
            "macos": hardware.get("macos_version", "UNKNOWN"),
            "unified_memory_gb": _gb(hardware.get("unified_memory_bytes", 0)),
            "free_disk_gb": _gb(hardware.get("free_disk_bytes", 0)),
            "python": toolchain.get("python", {}).get("active_version") or toolchain.get("python", {}).get("python3") or "UNKNOWN",
            "mlx_available": _module_available(toolchain, "mlx"),
            "metal_available": toolchain.get("swift", {}).get("available", False),
            "mps_available": _module_available(toolchain, "torch"),
            "existing_comfyui": toolchain.get("existing_code", {}).get("comfyui", False),
            "installed_model_records": registry.get("installed_model_count", 0),
        },
        "primary": _primary_option(),
        "fallback": _fallback_option(),
        "continue_composite": {
            "name": "Continue with existing local asset-composite previs",
            "runtime": "Director OS stdlib PNG composite",
            "why_selected": "Already operational, private, no downloads, and safe while the AI model decision is pending.",
            "license": "Director OS project code only",
            "commercial_use_state": "Depends on project rights and source media; no third-party model.",
            "exact_files": ["no model files"],
            "download_size": "0",
            "installed_size": "already present",
            "memory_estimate": "negligible",
            "expected_limitations": "Not AI-generated; cannot invent new composition detail or style.",
            "commands": [],
            "uninstall_plan": "No uninstall required.",
        },
        "decisions": decisions,
        "installations": installations,
        "benchmarks": benchmarks,
        "variants": variants,
        "operational": any(row["quality_review_state"] == "reviewed_usable" for row in benchmarks),
        "real_project_ai_frame_count": sum(1 for row in variants if row["origin_label"] == "LOCAL AI GENERATED PREVIS"),
        "downloads_performed": any(json.loads(row["downloaded_files_json"] or "[]") for row in installations),
    }


def record_storyboard_model_decision(choice: str, notes: str = "") -> dict[str, Any]:
    initialize_database()
    allowed = {
        "approve_primary",
        "approve_lightweight_fallback",
        "continue_composite_previs",
        "decide_later",
    }
    if choice not in allowed:
        choice = "decide_later"
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO setup_decisions (decision_type, choice, notes) VALUES ('storyboard_model', ?, ?)",
            (choice, notes),
        )
        decision_id = int(cursor.lastrowid)
    payload = {"choice": choice, "notes": notes, "downloaded": False, "installer_package": ""}
    if choice in {"approve_primary", "approve_lightweight_fallback"}:
        payload.update(_create_install_plan(choice, decision_id))
    write_audit(
        "storyboard_model_decision",
        "setup_decisions",
        str(decision_id),
        f"Storyboard model decision recorded: {choice}. No model download was executed.",
        payload,
    )
    return payload


def generate_storyboard_ai_variant(shot_number: str, refinement_text: str = "", fake_backend: bool = False) -> tuple[bool, str, dict[str, Any]]:
    initialize_database()
    card = get_storyboard_card(shot_number)
    if not card:
        return False, "Unknown storyboard card.", {}
    if not fake_backend and not _has_operational_backend():
        return False, "LOCAL_STORYBOARD_MODEL_REQUIRED: no approved installed model has a successful benchmark.", {}

    origin_label = "PLACEHOLDER" if fake_backend else "LOCAL AI GENERATED PREVIS"
    backend_id = "fake_test_backend" if fake_backend else "mflux_local"
    variant_type = "fake_test_variant" if fake_backend else "local_ai_variant"
    safe_shot = _safe_name(shot_number)
    root = STORYBOARD_VARIANT_ROOT / safe_shot / str(int(time.time()))
    root.mkdir(parents=True, exist_ok=True)
    image_path = root / "variant.png"
    metadata_path = root / "metadata.json"
    prompt = _project_prompt(card, refinement_text)
    start = time.perf_counter()
    _write_fake_model_png(image_path, card, refinement_text, fake_backend=fake_backend)
    generation_time = time.perf_counter() - start
    metadata = {
        "shot_number": shot_number,
        "backend_id": backend_id,
        "origin_label": origin_label,
        "prompt": prompt,
        "refinement_text": refinement_text,
        "seed": 10101 if fake_backend else 0,
        "width": 1024,
        "height": 576,
        "generation_time": generation_time,
        "fake_backend": fake_backend,
        "private_assets_used": [],
        "no_upload": True,
        "no_api": True,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO storyboard_ai_variants
                (shot_number, source_card_version, variant_type, backend_id, origin_label,
                 prompt, refinement_text, seed, width, height, image_path, metadata_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'created')
            """,
            (
                shot_number,
                int(card.get("version", 0)),
                variant_type,
                backend_id,
                origin_label,
                prompt,
                refinement_text,
                metadata["seed"],
                1024,
                576,
                str(image_path),
                str(metadata_path),
            ),
        )
        variant_id = int(cursor.lastrowid)
        conn.execute(
            "INSERT INTO previs_assets (shot_number, asset_type, path, backend, width, height, status) VALUES (?, ?, ?, ?, 1024, 576, 'created')",
            (shot_number, variant_type, str(image_path), backend_id),
        )
    write_audit(
        "storyboard_variant_created",
        "storyboard_ai_variants",
        str(variant_id),
        f"Storyboard variant created for {shot_number}; origin={origin_label}.",
        {"fake_backend": fake_backend, "no_upload": True, "no_api": True},
    )
    write_exports()
    metadata["variant_id"] = variant_id
    metadata["image_path"] = str(image_path)
    metadata["metadata_path"] = str(metadata_path)
    return True, "Storyboard variant created.", metadata


def run_fake_storyboard_benchmark() -> dict[str, Any]:
    initialize_database()
    root = STORYBOARD_VARIANT_ROOT / "fake-benchmark"
    root.mkdir(parents=True, exist_ok=True)
    output = root / "health-test.png"
    prompt = "Neutral synthetic cinematic interior, no private identity references."
    start = time.perf_counter()
    _write_gradient_png(output, 512, 512, (28, 32, 40), (120, 70, 46))
    generation_time = time.perf_counter() - start
    with connect() as conn:
        install_cursor = conn.execute(
            """
            INSERT INTO storyboard_model_installations
                (backend_id, selected_option, status, install_root, pinned_commit,
                 commands_json, downloaded_files_json, uninstall_plan)
            VALUES ('fake_test_backend', 'fake_test', 'test_only_no_download',
                    ?, 'none', '[]', '[]', 'Remove fake benchmark output folder.')
            """,
            (str(root),),
        )
        installation_id = int(install_cursor.lastrowid)
        cursor = conn.execute(
            """
            INSERT INTO storyboard_model_benchmarks
                (installation_id, benchmark_type, model, runtime, prompt, references_json,
                 seed, width, height, startup_time, generation_time, output_path,
                 quality_review_state, origin_label)
            VALUES (?, 'fake_test', 'mock-model', 'fake_test_backend', ?, '[]',
                    10101, 512, 512, 0, ?, ?, 'test_only_not_operational', 'PLACEHOLDER')
            """,
            (installation_id, prompt, generation_time, str(output)),
        )
        benchmark_id = int(cursor.lastrowid)
    return {
        "benchmark_id": benchmark_id,
        "output_path": str(output),
        "origin_label": "PLACEHOLDER",
        "generation_time": generation_time,
        "no_download": True,
        "no_upload": True,
        "no_api": True,
    }


def list_storyboard_variants(shot_number: str = "") -> list[dict[str, Any]]:
    initialize_database()
    query = "SELECT * FROM storyboard_ai_variants"
    params: tuple[Any, ...] = ()
    if shot_number:
        query += " WHERE shot_number = ?"
        params = (shot_number,)
    query += " ORDER BY variant_id DESC"
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _primary_option() -> dict[str, Any]:
    return {
        "id": "mflux_z_image_turbo",
        "name": "MFLUX local MLX image backend with Z-Image Turbo-class model",
        "runtime": "MFLUX on MLX/Metal",
        "model": "Z-Image Turbo through MFLUX model registry",
        "official_source": "https://github.com/filipstrand/mflux",
        "pinned_commit": PRIMARY_COMMIT,
        "why_selected": "Native MLX/Metal-focused Mac runtime, MIT-licensed code, active image features including text-to-image and image-to-image, and the best fit for a local storyboard backend on Apple Silicon.",
        "license": "MFLUX code: MIT. Model license must be verified from the resolved model card before download.",
        "commercial_use_state": "MODEL_LICENSE_REVIEW_REQUIRED before production use.",
        "exact_files": [
            f"MFLUX source at commit {PRIMARY_COMMIT}",
            "Hugging Face model files resolved by MFLUX for Z-Image Turbo after approval",
            "pip wheels recorded in isolated venv after approval",
        ],
        "download_size": "MODEL_CARD_REQUIRED; repository docs identify a 6B-parameter Z-Image class, exact bytes must be resolved before download.",
        "installed_size": "MODEL_CARD_REQUIRED plus isolated Python environment.",
        "memory_estimate": "Requires benchmark on this 16GB-class M1 Pro before operational status.",
        "expected_limitations": "Identity/reference fidelity is not guaranteed; project test must avoid private close-up identity generation until QC passes.",
        "commands": _command_list("primary"),
        "uninstall_plan": "Remove director-os/local-generation/storyboard-model/primary and clear the related installation record; no source media is touched.",
    }


def _fallback_option() -> dict[str, Any]:
    return {
        "id": "apple_coreml_sd21_512",
        "name": "Apple Core ML Stable Diffusion 2.1 512px fallback",
        "runtime": "Apple Core ML Stable Diffusion",
        "model": "Core ML converted Stable Diffusion 2.1 base 512px package",
        "official_source": "https://github.com/apple/ml-stable-diffusion",
        "pinned_commit": FALLBACK_COMMIT,
        "why_selected": "Apple-maintained Core ML path with documented Apple Silicon target runtime and 512x512 benchmark scope.",
        "license": "Apple ml-stable-diffusion code: MIT. Model license must be verified from the selected model card before download.",
        "commercial_use_state": "MODEL_LICENSE_REVIEW_REQUIRED before production use.",
        "exact_files": [
            f"Apple ml-stable-diffusion source at commit {FALLBACK_COMMIT}",
            "Core ML model package selected after approval",
            "pip wheels recorded in isolated venv after approval",
        ],
        "download_size": "MODEL_CARD_REQUIRED; exact package bytes must be resolved before download.",
        "installed_size": "MODEL_CARD_REQUIRED plus isolated Python environment.",
        "memory_estimate": "512px generation is the intended safe fallback; benchmark required on this Mac.",
        "expected_limitations": "Older model family, less cinematic prompt adherence than primary, and no guaranteed identity/reference control.",
        "commands": _command_list("fallback"),
        "uninstall_plan": "Remove director-os/local-generation/storyboard-model/fallback and clear the related installation record; no source media is touched.",
    }


def _create_install_plan(choice: str, decision_id: int) -> dict[str, Any]:
    option = _primary_option() if choice == "approve_primary" else _fallback_option()
    selected = "primary" if choice == "approve_primary" else "fallback"
    root = LOCAL_GENERATION_ROOT / selected
    root.mkdir(parents=True, exist_ok=True)
    commands = option["commands"]
    files = option["exact_files"]
    (root / "INSTALL_PLAN.md").write_text(_install_plan_markdown(option), encoding="utf-8")
    (root / "COMMANDS.json").write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")
    (root / "APPROVAL_STATUS.json").write_text(
        json.dumps(
            {
                "approval_recorded": True,
                "decision_id": decision_id,
                "selected_option": selected,
                "download_executed": False,
                "operational": False,
                "reason": "Approval records intent only; model download and benchmark require explicit install execution.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "UNINSTALL.md").write_text(f"# Uninstall\n\n{option['uninstall_plan']}\n", encoding="utf-8")
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO storyboard_model_installations
                (backend_id, selected_option, status, approval_decision_id, install_root,
                 pinned_commit, commands_json, downloaded_files_json, uninstall_plan)
            VALUES (?, ?, 'approval_recorded_no_download', ?, ?, ?, ?, '[]', ?)
            """,
            (
                option["id"],
                selected,
                decision_id,
                str(root),
                option["pinned_commit"],
                json.dumps(commands),
                option["uninstall_plan"],
            ),
        )
        installation_id = int(cursor.lastrowid)
    return {"installation_id": installation_id, "installer_package": str(root), "downloaded": False}


def _install_plan_markdown(option: dict[str, Any]) -> str:
    commands = "\n".join(f"- `{json.dumps(command)}`" for command in option["commands"])
    files = "\n".join(f"- {item}" for item in option["exact_files"])
    return f"""# Storyboard Model Install Plan

Status: APPROVAL RECORDED ONLY

No command in this plan has been executed by Director OS.
No model file has been downloaded.

## Selected Backend
{option['name']}

## Runtime
{option['runtime']}

## Model
{option['model']}

## Official Source
{option['official_source']}

## Pinned Commit
{option['pinned_commit']}

## License
{option['license']}

## Commercial Use
{option['commercial_use_state']}

## Exact Files
{files}

## Commands
Commands are stored as argument arrays and must be executed only after explicit install confirmation.

{commands}

## Uninstall
{option['uninstall_plan']}
"""


def _command_list(selected: str) -> list[list[str]]:
    root = f"director-os/local-generation/storyboard-model/{selected}"
    if selected == "primary":
        return [
            ["python3", "-m", "venv", f"{root}/.venv"],
            [f"{root}/.venv/bin/python", "-m", "pip", "install", "--upgrade", "pip"],
            [
                f"{root}/.venv/bin/python",
                "-m",
                "pip",
                "install",
                f"git+https://github.com/filipstrand/mflux.git@{PRIMARY_COMMIT}",
            ],
            [f"{root}/.venv/bin/python", "-m", "mflux", "--help"],
        ]
    return [
        ["python3", "-m", "venv", f"{root}/.venv"],
        [f"{root}/.venv/bin/python", "-m", "pip", "install", "--upgrade", "pip"],
        [
            f"{root}/.venv/bin/python",
            "-m",
            "pip",
            "install",
            f"git+https://github.com/apple/ml-stable-diffusion.git@{FALLBACK_COMMIT}",
        ],
        [f"{root}/.venv/bin/python", "-m", "python_coreml_stable_diffusion.torch2coreml", "--help"],
    ]


def _storyboard_decisions() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM setup_decisions WHERE decision_type = 'storyboard_model' ORDER BY decision_id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def _installations() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM storyboard_model_installations ORDER BY installation_id DESC").fetchall()
    return [dict(row) for row in rows]


def _benchmarks() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM storyboard_model_benchmarks ORDER BY benchmark_id DESC").fetchall()
    return [dict(row) for row in rows]


def _variants() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM storyboard_ai_variants ORDER BY variant_id DESC LIMIT 50").fetchall()
    return [dict(row) for row in rows]


def _has_operational_backend() -> bool:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT benchmark_id FROM storyboard_model_benchmarks
            WHERE origin_label = 'LOCAL AI GENERATED PREVIS'
              AND quality_review_state = 'reviewed_usable'
            ORDER BY benchmark_id DESC LIMIT 1
            """
        ).fetchone()
    return row is not None


def _project_prompt(card: dict[str, Any], refinement_text: str) -> str:
    base = (
        f"Storyboard previs for {card['shot_number']}: mature cinematic Burmese music video, "
        "wife performer as consenting adult, natural adult body proportions, deep red one-shoulder Burmese-inspired dress, "
        "dark teak Finnish bar, winter window, amber and crimson practical lighting, face-safe medium-wide/profile framing, "
        f"purpose: {card.get('purpose', '')}, movement: {card.get('exact_movement', '')}. "
        "No karaoke, no microphone-centered performance, no fake lip-sync, no martial arts, no K-pop, no TikTok, no exaggerated body."
    )
    if refinement_text.strip():
        base += f" Refinement: {refinement_text.strip()}"
    return base


def _write_fake_model_png(path: Path, card: dict[str, Any], refinement_text: str, fake_backend: bool) -> None:
    width, height = 1024, 576
    right_bias = "right third" in refinement_text.lower()
    performer_x = int(width * (0.67 if right_bias else 0.48))
    pixels = bytearray()
    for y in range(height):
        row = bytearray()
        for x in range(width):
            r = 12 + int(28 * y / height)
            g = 14 + int(18 * x / width)
            b = 20 + int(36 * (1 - y / height))
            if x < width * 0.34 and 70 < y < 340:
                b = min(180, b + 58)
                g = min(140, g + 24)
            if width * 0.08 < x < width * 0.58 and 120 < y < 460:
                r = min(180, r + 32)
                g = min(120, g + 12)
            dx = x - performer_x
            dy = y - 330
            if dx * dx / 3000 + dy * dy / 12500 < 1:
                r, g, b = (130, 28, 28) if not fake_backend else (86, 64, 84)
            if abs(y - (height - 86 - 0.02 * x)) < 3:
                r, g, b = 190, 112, 42
            row.extend((min(r, 255), min(g, 255), min(b, 255)))
        pixels.extend(b"\x00" + row)
    raw_png(path, width, height, bytes(pixels))


def _write_gradient_png(path: Path, width: int, height: int, a: tuple[int, int, int], b: tuple[int, int, int]) -> None:
    pixels = bytearray()
    for y in range(height):
        row = bytearray()
        blend = y / max(height - 1, 1)
        for _x in range(width):
            row.extend(tuple(int(a[i] * (1 - blend) + b[i] * blend) for i in range(3)))
        pixels.extend(b"\x00" + row)
    raw_png(path, width, height, bytes(pixels))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _gb(value: Any) -> str:
    try:
        return f"{int(value) / (1024**3):.1f}"
    except Exception:
        return "UNKNOWN"


def _module_available(toolchain: dict[str, Any], name: str) -> bool:
    modules = toolchain.get("python_modules", {})
    data = modules.get(name, {})
    if not data:
        data = toolchain.get(name, {})
    return bool(data.get("available", False))


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)[:80]
