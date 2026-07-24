from __future__ import annotations

from .base_connector import BaseConnector


class ManualUploadConnector(BaseConnector):
    name = "manual_upload"
    official_api = "not_applicable"
    local_possible = False
    manual_upload_possible = True
    enabled = False
