from __future__ import annotations

from .base_connector import BaseConnector


class OpenAIVideoConnector(BaseConnector):
    name = "openai_video"
    official_api = "unknown_current_video_availability_must_be_verified"
    local_possible = False
    manual_upload_possible = False
    enabled = False
