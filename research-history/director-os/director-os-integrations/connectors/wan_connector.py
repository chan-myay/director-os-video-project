from __future__ import annotations

from .base_connector import BaseConnector


class WanConnector(BaseConnector):
    name = "wan"
    official_api = "not_applicable_local_model"
    local_possible = True
    manual_upload_possible = False
    enabled = False
