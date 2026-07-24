from __future__ import annotations

from app.services.db import connect, initialize_database


def approved_pronunciation_overrides() -> dict[str, str]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute("SELECT original_text, pronunciation_helper FROM pronunciation_overrides WHERE status = 'approved'").fetchall()
    return {row["original_text"]: row["pronunciation_helper"] for row in rows}
