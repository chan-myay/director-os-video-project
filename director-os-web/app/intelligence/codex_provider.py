from __future__ import annotations

import shutil
import json
import tempfile
from pathlib import Path
from typing import Any

from app.config import REPO_ROOT
from app.intelligence.context_builder import stage_prompt
from app.intelligence.provider import IntelligenceProvider, ProviderResponse
from app.intelligence.response_validator import parse_json_object, validate_stage_response
from app.intelligence.run_security import ensure_workspace, run_process
from app.intelligence.schemas import STAGE_SCHEMA


class CodexProvider(IntelligenceProvider):
    name = "codex_cli"

    def __init__(self, project_root: str | Path = REPO_ROOT) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.codex_path = shutil.which("codex")
        self.version = self._version()

    def _version(self) -> str:
        if not self.codex_path:
            return "missing"
        result = run_process([self.codex_path, "--version"], self.project_root, 20)
        return (result.stdout or result.stderr or "unknown").strip().splitlines()[-1]

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "available": bool(self.codex_path),
            "runtime": self.codex_path or "missing",
            "version": self.version,
            "privacy_mode": "local workspace; no private upload requested by Director OS",
            "research_permission": "web search only when explicitly enabled by Codex runtime or separate research service",
        }

    def complete_stage(self, stage: str, context: dict[str, Any], timeout: int = 120) -> ProviderResponse:
        if not self.codex_path:
            raise RuntimeError("Codex CLI not found.")
        workspace = ensure_workspace(context["project_path"], self.project_root)
        prompt = stage_prompt(context)
        with tempfile.TemporaryDirectory(prefix="director-os-codex-") as temp_dir:
            schema_path = Path(temp_dir) / "stage_schema.json"
            output_path = Path(temp_dir) / "stage_output.json"
            schema_path.write_text(json.dumps(STAGE_SCHEMA), encoding="utf-8")
            args = [
                self.codex_path,
                "exec",
                "--skip-git-repo-check",
                "--ephemeral",
                "--color",
                "never",
                "--sandbox",
                "read-only",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "-C",
                str(workspace),
                "-",
            ]
            result = run_process(args, workspace, timeout, stdin=prompt)
            final_message = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
            combined = "\n".join(part for part in [final_message, result.stdout, result.stderr] if part)
            try:
                data = validate_stage_response(parse_json_object(combined), stage)
            except Exception:
                if result.exit_status != 0:
                    raise RuntimeError(f"Codex stage failed: {result.stderr[-1000:]}")
                raise
        return ProviderResponse(
            provider_name=self.name,
            provider_version=self.version,
            raw_text=result.stdout,
            data=data,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_status=result.exit_status,
            timed_out=result.timed_out,
            started_at=result.started_at,
            ended_at=result.ended_at,
        )
