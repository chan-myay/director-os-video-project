from __future__ import annotations

import json
from typing import Any, Optional

from app.services.db import connect, initialize_database


def write_audit(
    event_type: str,
    entity_type: str,
    entity_id: str,
    summary: str,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    initialize_database()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (event_type, entity_type, entity_id, summary, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_type, entity_type, entity_id, summary, json.dumps(metadata or {}, sort_keys=True)),
        )


def list_audit_logs(limit: int = 200) -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
