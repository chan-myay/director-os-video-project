from __future__ import annotations

from .base_connector import BaseConnector


class ComfyUIConnector(BaseConnector):
    name = "comfyui"
    official_api = "local_http_api"
    local_possible = True
    manual_upload_possible = False
    enabled = False
