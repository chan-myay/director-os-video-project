from __future__ import annotations

from .base_connector import BaseConnector


class VeoConnector(BaseConnector):
    name = "veo"
    official_api = "google_vertex_or_product_dependent"
    local_possible = False
    manual_upload_possible = True
    enabled = False
