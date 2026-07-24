from __future__ import annotations

from .base_connector import BaseConnector


class KlingConnector(BaseConnector):
    name = "kling"
    official_api = "unknown_or_plan_dependent"
    local_possible = False
    manual_upload_possible = True
    enabled = False
