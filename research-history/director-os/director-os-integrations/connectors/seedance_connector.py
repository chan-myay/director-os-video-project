from __future__ import annotations

from .base_connector import BaseConnector


class SeedanceConnector(BaseConnector):
    name = "seedance"
    official_api = "unknown_or_region_dependent"
    local_possible = False
    manual_upload_possible = True
    enabled = False
