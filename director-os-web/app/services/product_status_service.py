from __future__ import annotations

from app.config import PRODUCT_ROOT
from app.services.engine_reader import read_text, relative


PRODUCT_FILES = [
    "PRODUCT_VISION.md",
    "PUBLIC_SAAS_ARCHITECTURE.md",
    "BURMESE_FIRST_STRATEGY.md",
    "REFERENCE_LIBRARY_STRATEGY.md",
    "API_CONNECTOR_MATRIX.md",
    "MVP_DEFINITION.md",
    "WORLD_CLASS_BAR.md",
    "PUBLIC_READY_V0_3_REPORT.md",
]


def product_documents() -> list[dict[str, str]]:
    docs = []
    for name in PRODUCT_FILES:
        path = PRODUCT_ROOT / name
        docs.append({"name": name, "path": relative(path), "preview": read_text(path, 1800)})
    return docs


def product_status() -> dict[str, object]:
    return {
        "root": relative(PRODUCT_ROOT),
        "status": "Public-ready architecture planned; local-only implementation shell.",
        "documents": product_documents(),
    }
