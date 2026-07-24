from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from app.config import ENGINE_ROOT, INTEGRATIONS_ROOT, REFERENCE_ROOT
from app.services.db import connect, initialize_database
from app.services.engine_reader import read_text, relative


PROJECT_SLUG = "burmese-music-video"
PROJECT_NAME = "Burmese music video - A Chit Mae Zat Lan"


def _purpose_from_shot_pack(path: Path) -> str:
    intent = read_text(path / "SHOT_INTENT.md")
    for line in intent.splitlines():
        if line.startswith("Purpose:"):
            return line.replace("Purpose:", "").strip()
    return "UNKNOWN"


def _renderer_from_filename(filename: str) -> str:
    name = filename.lower()
    if "kling" in name:
        return "kling"
    if "seedance" in name:
        return "seedance"
    if "wan" in name:
        return "wan"
    if "veo" in name:
        return "veo"
    if "generic" in name:
        return "generic"
    if "approval" in name:
        return "approval"
    if "qc" in name:
        return "qc"
    return "review"


def _seed_project(conn) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO projects (slug, name, status)
        VALUES (?, ?, 'local_control_room')
        """,
        (PROJECT_SLUG, PROJECT_NAME),
    )
    row = conn.execute("SELECT id FROM projects WHERE slug = ?", (PROJECT_SLUG,)).fetchone()
    return int(row["id"])


def seed_from_existing_files() -> None:
    initialize_database()
    with connect() as conn:
        project_id = _seed_project(conn)

        shot_root = ENGINE_ROOT / "shot-packs"
        if shot_root.exists():
            for pack_dir in sorted(path for path in shot_root.iterdir() if path.is_dir()):
                conn.execute(
                    """
                    INSERT INTO shot_packs (project_id, shot_id, path, purpose, status)
                    VALUES (?, ?, ?, ?, 'seeded_from_engine')
                    ON CONFLICT(shot_id) DO UPDATE SET
                        path=excluded.path,
                        purpose=excluded.purpose,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (project_id, pack_dir.name, relative(pack_dir), _purpose_from_shot_pack(pack_dir)),
                )

        generated_root = ENGINE_ROOT / "generated-requests"
        if generated_root.exists():
            for request_dir in sorted(path for path in generated_root.iterdir() if path.is_dir()):
                shot = conn.execute(
                    "SELECT id FROM shot_packs WHERE shot_id = ?",
                    (request_dir.name,),
                ).fetchone()
                if not shot:
                    continue
                for file_path in sorted(path for path in request_dir.iterdir() if path.is_file()):
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO generated_requests
                            (shot_pack_id, filename, path, renderer, status)
                        VALUES (?, ?, ?, ?, 'review_only')
                        """,
                        (int(shot["id"]), file_path.name, relative(file_path), _renderer_from_filename(file_path.name)),
                    )

        _seed_connectors(conn)
        _seed_reference_sites(conn)


def _seed_connectors(conn) -> None:
    status_path = INTEGRATIONS_ROOT / "CONNECTOR_STATUS.yaml"
    raw = read_text(status_path)
    current = None
    data: dict[str, dict[str, str]] = {}
    for line in raw.splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            key = line.strip().rstrip(":")
            if key not in {"no_cloud_api_calls", "no_paid_api_calls", "no_upload_without_approval", "no_generation", "no_media_copying"}:
                current = key
                data[current] = {}
        elif current and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            data[current][key] = value.strip().strip('"')

    for name, fields in data.items():
        conn.execute(
            """
            INSERT INTO connector_status
                (name, status, enabled, local_possible, private_media_risk, next_step, raw_source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                status=excluded.status,
                enabled=excluded.enabled,
                local_possible=excluded.local_possible,
                private_media_risk=excluded.private_media_risk,
                next_step=excluded.next_step,
                raw_source=excluded.raw_source,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                name,
                fields.get("status", "UNKNOWN"),
                1 if fields.get("enabled", "false") == "true" else 0,
                1 if fields.get("local_possible", "false") == "true" else 0,
                fields.get("private_media_risk", "UNKNOWN"),
                fields.get("next_step", "UNKNOWN"),
                raw,
            ),
        )


def _seed_reference_sites(conn) -> None:
    existing = conn.execute("SELECT COUNT(*) AS count FROM reference_moodboards").fetchone()["count"]
    if existing:
        return

    source_path = REFERENCE_ROOT / "reference_sites.yaml"
    raw = read_text(source_path)
    current = None
    data: dict[str, dict[str, str]] = {}
    for line in raw.splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            current = line.strip().rstrip(":")
            if current not in {"required_metadata"}:
                data[current] = {}
        elif current and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            data[current][key] = value.strip().strip('"')

    for name, fields in data.items():
        url = fields.get("url")
        if not url:
            continue
        conn.execute(
            """
            INSERT INTO reference_moodboards
                (url, title, source, rights_notes, do_not_copy_warning)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                url,
                name.replace("_", " ").title(),
                name,
                "Seeded from reference_sites.yaml. Store URL and notes only.",
                "Do not copy or rehost copyrighted reference media.",
            ),
        )


def workflow_summary() -> dict[str, Any]:
    initialize_database()
    seed_from_existing_files()
    with connect() as conn:
        counts = {}
        for table in [
            "projects",
            "shot_packs",
            "generated_requests",
            "approval_gates",
            "qc_reviews",
            "connector_status",
            "reference_moodboards",
            "audit_logs",
            "generation_jobs",
            "job_assets",
            "job_events",
            "job_outputs",
            "manual_exports",
            "imported_results",
            "result_media",
            "result_reviews",
            "result_decisions",
        ]:
            counts[table] = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
        project = conn.execute("SELECT * FROM projects WHERE slug = ?", (PROJECT_SLUG,)).fetchone()
        shots = conn.execute("SELECT * FROM shot_packs ORDER BY shot_id").fetchall()
    return {"project": dict(project) if project else None, "counts": counts, "shot_packs": [dict(row) for row in shots]}


def get_shot_pack_record(shot_id: str) -> Optional[dict[str, Any]]:
    initialize_database()
    seed_from_existing_files()
    with connect() as conn:
        row = conn.execute("SELECT * FROM shot_packs WHERE shot_id = ?", (shot_id,)).fetchone()
    return dict(row) if row else None


def connector_records() -> list[dict[str, Any]]:
    initialize_database()
    seed_from_existing_files()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM connector_status ORDER BY name").fetchall()
    return [dict(row) for row in rows]
