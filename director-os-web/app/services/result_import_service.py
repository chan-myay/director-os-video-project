from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Optional

from app.config import MAX_RESULT_UPLOAD_BYTES, RESULT_MEDIA_ROOT
from app.services.audit_service import write_audit
from app.services.db import connect, initialize_database
from app.services.engine_reader import read_text
from app.services.media_probe_service import extract_contact_sheet, extract_poster, probe_video
from app.services.workflow_service import PROJECT_SLUG


ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm"}
PROJECT_FOLDER = PROJECT_SLUG


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return safe or "result.mp4"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_id() -> int:
    with connect() as conn:
        row = conn.execute("SELECT id FROM projects WHERE slug = ?", (PROJECT_SLUG,)).fetchone()
    if not row:
        raise RuntimeError("project is not seeded")
    return int(row["id"])


def _export_record(export_id: int) -> Optional[dict[str, Any]]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM manual_exports WHERE export_id = ?", (export_id,)).fetchone()
    return dict(row) if row else None


def import_result_from_path(
    source_path_text: str,
    shot_id: str,
    job_id: int,
    export_id: int,
    renderer: str,
    is_test: bool = False,
) -> tuple[bool, str, Optional[int]]:
    initialize_database()
    source_path = Path(source_path_text).expanduser().resolve()
    if not source_path.exists() or not source_path.is_file():
        return False, "Source result file does not exist.", None
    if source_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False, "Unsupported result extension. Use mp4, mov, or webm.", None
    file_size = source_path.stat().st_size
    if file_size > MAX_RESULT_UPLOAD_BYTES:
        return False, "Result file exceeds local size limit.", None

    export = _export_record(export_id)
    if not export:
        return False, "Unknown manual export.", None

    metadata = probe_video(source_path)
    digest = sha256_file(source_path)
    project_id = _project_id()
    original_filename = sanitize_filename(source_path.name)

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO imported_results
                (project_id, shot_id, job_id, export_id, renderer, original_filename,
                 stored_path, file_size, duration, width, height, fps, sha256, status,
                 is_test, codec)
            VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?, ?, 'awaiting_review', ?, ?)
            """,
            (
                project_id,
                shot_id,
                job_id,
                export_id,
                renderer,
                original_filename,
                file_size,
                metadata["duration"],
                metadata["width"],
                metadata["height"],
                metadata["fps"],
                digest,
                1 if is_test else 0,
                metadata["codec"],
            ),
        )
        result_id = int(cursor.lastrowid)

    result_dir = RESULT_MEDIA_ROOT / PROJECT_FOLDER / shot_id / str(result_id)
    result_dir.mkdir(parents=True, exist_ok=False)
    stored_path = result_dir / original_filename
    shutil.copy2(str(source_path), str(stored_path))
    poster_path = result_dir / "poster.jpg"
    contact_sheet_path = result_dir / "contact-sheet.jpg"
    extract_poster(stored_path, poster_path)
    extract_contact_sheet(stored_path, contact_sheet_path)

    metadata_path = result_dir / "metadata.json"
    metadata_payload = {
        "result_id": result_id,
        "project": PROJECT_FOLDER,
        "shot_id": shot_id,
        "job_id": job_id,
        "export_id": export_id,
        "renderer": renderer,
        "original_filename": original_filename,
        "stored_path": str(stored_path),
        "file_size": file_size,
        "sha256": digest,
        **metadata,
    }
    metadata_path.write_text(json.dumps(metadata_payload, indent=2, sort_keys=True), encoding="utf-8")
    (result_dir / "IMPORT_RECORD.md").write_text(_import_record(metadata_payload), encoding="utf-8")
    (result_dir / "QC_RESULT.md").write_text("# QC Result\n\nNo result QC submitted yet.\n", encoding="utf-8")
    (result_dir / "DECISION.md").write_text("# Decision\n\nNo decision recorded yet.\n", encoding="utf-8")

    with connect() as conn:
        conn.execute(
            """
            UPDATE imported_results
            SET stored_path = ?, poster_path = ?, contact_sheet_path = ?
            WHERE result_id = ?
            """,
            (str(stored_path), str(poster_path), str(contact_sheet_path), result_id),
        )
        for media_type, path in [
            ("video", stored_path),
            ("poster", poster_path),
            ("contact_sheet", contact_sheet_path),
            ("metadata", metadata_path),
        ]:
            conn.execute(
                """
                INSERT INTO result_media (result_id, media_type, path, file_size, sha256)
                VALUES (?, ?, ?, ?, ?)
                """,
                (result_id, media_type, str(path), path.stat().st_size, sha256_file(path) if path.is_file() else ""),
            )

    write_audit(
        "result_imported",
        "imported_results",
        str(result_id),
        f"Imported generated result for {shot_id}",
        {"result_id": result_id, "job_id": job_id, "export_id": export_id, "renderer": renderer, "is_test": is_test},
    )
    return True, "Result imported.", result_id


def _import_record(metadata: dict[str, Any]) -> str:
    return f"""# Import Record

- Result ID: {metadata['result_id']}
- Shot ID: {metadata['shot_id']}
- Job ID: {metadata['job_id']}
- Export ID: {metadata['export_id']}
- Renderer: {metadata['renderer']}
- Original filename: {metadata['original_filename']}
- Stored path: {metadata['stored_path']}
- SHA-256: {metadata['sha256']}
- Duration: {metadata['duration']}
- Width: {metadata['width']}
- Height: {metadata['height']}
- FPS: {metadata['fps']}
- Codec: {metadata['codec']}

No API call, upload, or generation was performed by Director OS during import.
"""


def list_results(show_tests: bool = False) -> list[dict[str, Any]]:
    initialize_database()
    where = "" if show_tests else "WHERE is_test = 0"
    with connect() as conn:
        rows = conn.execute(f"SELECT * FROM imported_results {where} ORDER BY result_id DESC").fetchall()
    return [dict(row) for row in rows]


def get_result(result_id: int) -> Optional[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        row = conn.execute("SELECT * FROM imported_results WHERE result_id = ?", (result_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["reviews"] = [dict(r) for r in conn.execute("SELECT * FROM result_reviews WHERE result_id = ? ORDER BY review_id DESC", (result_id,)).fetchall()]
        result["decisions"] = [dict(d) for d in conn.execute("SELECT * FROM result_decisions WHERE result_id = ? ORDER BY decision_id DESC", (result_id,)).fetchall()]
        result["media"] = [dict(m) for m in conn.execute("SELECT * FROM result_media WHERE result_id = ? ORDER BY id", (result_id,)).fetchall()]
    result["import_record"] = read_text(Path(result["stored_path"]).parent / "IMPORT_RECORD.md", 8000)
    result["qc_result"] = read_text(Path(result["stored_path"]).parent / "QC_RESULT.md", 8000)
    result["decision_text"] = read_text(Path(result["stored_path"]).parent / "DECISION.md", 8000)
    return result


def result_counts() -> dict[str, int]:
    initialize_database()
    with connect() as conn:
        counts = {}
        for status in ["awaiting_review", "accepted", "rejected", "needs_face_correction"]:
            counts[status] = conn.execute(
                "SELECT COUNT(*) AS count FROM imported_results WHERE status = ? AND is_test = 0",
                (status,),
            ).fetchone()["count"]
    return counts
