from __future__ import annotations

from typing import Any

from app.services.audit_service import write_audit
from app.services.db import connect, initialize_database


DEFAULT_WARNING = "URL/reference only. Do not copy or rehost copyrighted media."


def list_moodboards() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM reference_moodboards ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def create_moodboard(form: dict[str, str]) -> tuple[bool, str]:
    initialize_database()
    url = form.get("url", "").strip()
    title = form.get("title", "").strip()
    source = form.get("source", "").strip()
    if not url or not title or not source:
        return False, "URL, title, and source are required."
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, "Moodboards store external URLs only."

    values = {
        "url": url,
        "title": title,
        "source": source,
        "shot_pack_id": form.get("shot_pack_id", "").strip(),
        "composition_notes": form.get("composition_notes", "").strip(),
        "lighting_notes": form.get("lighting_notes", "").strip(),
        "camera_notes": form.get("camera_notes", "").strip(),
        "color_notes": form.get("color_notes", "").strip(),
        "cultural_notes": form.get("cultural_notes", "").strip(),
        "rights_notes": form.get("rights_notes", "").strip(),
        "do_not_copy_warning": form.get("do_not_copy_warning", "").strip() or DEFAULT_WARNING,
    }

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reference_moodboards
                (url, title, source, shot_pack_id, composition_notes, lighting_notes,
                 camera_notes, color_notes, cultural_notes, rights_notes,
                 do_not_copy_warning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                values["url"],
                values["title"],
                values["source"],
                values["shot_pack_id"],
                values["composition_notes"],
                values["lighting_notes"],
                values["camera_notes"],
                values["color_notes"],
                values["cultural_notes"],
                values["rights_notes"],
                values["do_not_copy_warning"],
            ),
        )
        moodboard_id = cursor.lastrowid

    write_audit(
        "moodboard_created",
        "reference_moodboards",
        str(moodboard_id),
        f"Moodboard URL added: {title}",
        {"url": url, "source": source, "shot_pack_id": values["shot_pack_id"]},
    )
    return True, "Moodboard reference saved."
