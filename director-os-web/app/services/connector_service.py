from __future__ import annotations

from app.config import INTEGRATIONS_ROOT
from app.services.engine_reader import read_text, relative


CONNECTOR_STATUS = INTEGRATIONS_ROOT / "CONNECTOR_STATUS.yaml"


def connector_status() -> dict[str, str]:
    return {
        "path": relative(CONNECTOR_STATUS),
        "status": "All connectors disabled/stub-only in v0.3.",
        "content": read_text(CONNECTOR_STATUS),
    }
