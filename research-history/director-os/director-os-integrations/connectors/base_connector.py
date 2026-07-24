"""Base connector contracts for Director OS.

v0.3 connectors are intentionally disabled. They define the shape of future
integrations without performing uploads, paid API calls, renders, or generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


class ConnectorDisabledError(RuntimeError):
    """Raised when a v0.3 connector is asked to execute real work."""


@dataclass(frozen=True)
class ApprovalGate:
    renderer_approved: bool = False
    references_approved: bool = False
    final_request_approved: bool = False
    spend_limit_approved: bool = False
    privacy_risk_accepted: bool = False

    def is_open(self) -> bool:
        return all(
            [
                self.renderer_approved,
                self.references_approved,
                self.final_request_approved,
                self.spend_limit_approved,
                self.privacy_risk_accepted,
            ]
        )


@dataclass(frozen=True)
class ConnectorRequest:
    shot_id: str
    request_markdown: str
    reference_paths: list[str] = field(default_factory=list)
    spend_limit: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseConnector:
    name = "base"
    official_api: str = "unknown"
    local_possible: bool = False
    manual_upload_possible: bool = False
    enabled: bool = False

    def validate_request(self, request: ConnectorRequest, approval: ApprovalGate) -> list[str]:
        issues: list[str] = []
        if not request.shot_id:
            issues.append("shot_id is required")
        if not request.request_markdown.strip():
            issues.append("request_markdown is required")
        if not approval.is_open():
            issues.append("approval gate is closed")
        return issues

    def estimate_cost(self, request: ConnectorRequest) -> str:
        return "UNKNOWN - connector disabled in v0.3"

    def requires_upload(self) -> bool:
        return not self.local_possible

    def submit(self, request: ConnectorRequest, approval: ApprovalGate) -> str:
        raise ConnectorDisabledError(
            f"{self.name} connector is disabled in v0.3. No upload/API/generation is allowed."
        )

    def poll(self, job_id: str) -> dict[str, Any]:
        raise ConnectorDisabledError(f"{self.name} connector has no active jobs in v0.3.")

    def download_result(self, job_id: str, target_dir: str) -> str:
        raise ConnectorDisabledError(f"{self.name} connector cannot download results in v0.3.")
