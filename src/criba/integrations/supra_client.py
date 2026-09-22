"""Canonical typed HTTP client for the external SUPRA service.

This module is the only CRIBA-side authority for SUPRA HTTP routes.  UI,
console, and automation layers should depend on this client rather than
constructing endpoints themselves or importing SUPRA internals.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class SupraClientError(RuntimeError):
    """Raised when the SUPRA transport or response violates the client contract."""


@dataclass(frozen=True, slots=True)
class SupraClientConfig:
    endpoint: str = "http://127.0.0.1:8000"
    api_key: str = ""
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "SupraClientConfig":
        return cls(
            endpoint=os.getenv("SUPRA_ENDPOINT", "http://127.0.0.1:8000").strip(),
            api_key=os.getenv("SUPRA_API_KEY", "").strip(),
            timeout=float(os.getenv("SUPRA_TIMEOUT_SECONDS", "30")),
        )


class SupraProjectResult(BaseModel):
    """Stable subset returned by POST /api/v1/projects."""

    model_config = ConfigDict(extra="allow")

    status: Literal["success", "blocked"]
    status_scope: str = "WORKFLOW_EXECUTION_ONLY"
    completion_status: Literal["COMPLETED", "BLOCKED"]
    workflow_status: str
    verification_status: str
    scientific_status: str = "NOT_VALIDATED"
    project_id: str
    stage: str
    posture: dict[str, Any]

    @model_validator(mode="after")
    def reject_contradictory_completion(self) -> "SupraProjectResult":
        verification_blocks = self.verification_status in {"FAIL", "NOT_EVALUATED"}
        completed = (
            self.status == "success"
            and self.completion_status == "COMPLETED"
            and self.workflow_status == "COMPLETED"
            and self.stage == "COMPLETED"
        )
        blocked = (
            self.status == "blocked"
            and self.completion_status == "BLOCKED"
            and self.workflow_status != "COMPLETED"
            and self.stage != "COMPLETED"
        )
        if verification_blocks and completed:
            raise ValueError(
                "SUPRA contract violation: failed/unevaluated verification cannot be COMPLETED"
            )
        if not completed and not blocked:
            raise ValueError("SUPRA contract violation: inconsistent completion fields")
        return self


class SupraHealth(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    service: str
    version: str


class SupraProjectList(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    count: int
    projects: list[dict[str, Any]] = Field(default_factory=list)


class SupraClient:
    """Small typed client bound to SUPRA's real public HTTP API."""

    def __init__(
        self,
        config: SupraClientConfig | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config or SupraClientConfig.from_env()
        endpoint = self.config.endpoint.rstrip("/")
        if not endpoint:
            raise ValueError("SUPRA endpoint cannot be empty")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "CRIBA-SupraClient/1",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        self._client = httpx.Client(
            base_url=endpoint,
            timeout=self.config.timeout,
            headers=headers,
            transport=transport,
        )

    @staticmethod
    def validate_project_id(project_id: str) -> str:
        if not _PROJECT_ID_RE.fullmatch(project_id):
            raise ValueError("invalid SUPRA project_id")
        return project_id

    @classmethod
    def _project_path(cls, project_id: str) -> str:
        return "/api/v1/projects/" + quote(cls.validate_project_id(project_id), safe="")

    @staticmethod
    def _raise_for_response(response: httpx.Response, operation: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SupraClientError(
                f"SUPRA {operation} failed with HTTP {response.status_code}"
            ) from exc

    @staticmethod
    def _json_object(response: httpx.Response, operation: str) -> dict[str, Any]:
        try:
            value = response.json()
        except ValueError as exc:
            raise SupraClientError(f"SUPRA {operation} returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise SupraClientError(f"SUPRA {operation} returned a non-object JSON payload")
        return value

    def health(self) -> SupraHealth:
        response = self._client.get("/health")
        self._raise_for_response(response, "health")
        return SupraHealth.model_validate(self._json_object(response, "health"))

    def run_project(
        self,
        *,
        objective: str,
        domain: str = "general",
        allow_disruptive: bool = True,
        project_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        use_model: bool = False,
    ) -> SupraProjectResult:
        clean_objective = objective.strip()
        if len(clean_objective) < 5:
            raise ValueError("SUPRA objective must contain at least 5 characters")
        payload: dict[str, Any] = {
            "objective": clean_objective,
            "domain": domain,
            "allow_disruptive": allow_disruptive,
            "use_model": use_model,
        }
        if project_id is not None:
            payload["project_id"] = self.validate_project_id(project_id)
        if provider is not None:
            payload["provider"] = provider
        if model is not None:
            payload["model"] = model

        response = self._client.post("/api/v1/projects", json=payload)
        self._raise_for_response(response, "project execution")
        return SupraProjectResult.model_validate(
            self._json_object(response, "project execution")
        )

    def get_project(self, project_id: str) -> dict[str, Any]:
        response = self._client.get(self._project_path(project_id))
        self._raise_for_response(response, "project lookup")
        return self._json_object(response, "project lookup")

    def list_projects(self, *, limit: int = 20) -> SupraProjectList:
        if not 1 <= limit <= 50:
            raise ValueError("SUPRA project list limit must be between 1 and 50")
        response = self._client.get("/api/v1/projects", params={"limit": limit})
        self._raise_for_response(response, "project list")
        return SupraProjectList.model_validate(self._json_object(response, "project list"))

    def mcp(self, method: str, *, params: dict[str, Any] | None = None, request_id: int = 1) -> dict[str, Any]:
        if not method:
            raise ValueError("MCP method cannot be empty")
        response = self._client.post(
            "/api/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                **({"params": params} if params is not None else {}),
            },
        )
        self._raise_for_response(response, "MCP request")
        payload = self._json_object(response, "MCP request")
        if payload.get("jsonrpc") != "2.0":
            raise SupraClientError("SUPRA MCP response is not JSON-RPC 2.0")
        return payload

    def export_dossier(self, project_id: str) -> dict[str, Any]:
        path = "/api/v1/export/dossier/" + quote(self.validate_project_id(project_id), safe="")
        response = self._client.get(path)
        self._raise_for_response(response, "dossier export")
        return self._json_object(response, "dossier export")

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SupraClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
