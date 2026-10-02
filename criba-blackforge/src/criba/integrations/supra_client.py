"""Canonical typed HTTP client for the external SUPRA service.

This module is the only CRIBA-side authority for SUPRA HTTP routes.  UI,
console, and automation layers should depend on this client rather than
constructing endpoints themselves or importing SUPRA internals.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_CRIBA_SUPRA_ENVELOPE_VERSION = "criba-supra/1"


# SUPRA's CribaDossierRequest defaults. A dossier that omits one of these must
# still be the same payload as one that sends it explicitly, so CRIBA fills them
# before hashing. Keep this in step with the SUPRA model: the golden vectors in
# test_b01_client_server_agreement.py fail on any drift.
_DOSSIER_DEFAULTS: dict[str, Any] = {
    "run_id": "",
    "bloqueo": "",
    "origen_bloqueo": "",
    "evidence_delivered": [],
    "evidence_documented_as_used": [],
    "evidencia_utilizada": [],
    "supuestos": [],
}
_PROTOCOL_DEFAULTS: dict[str, Any] = {
    "comparacion": "",
    "metrica": "",
    "coste_permisos": "",
    "estado_prueba": "NO_EJECUTADA",
}


def _with_declared_defaults(dossier: Mapping[str, Any]) -> dict[str, Any]:
    """Return the semantic payload with every declared SUPRA default applied."""
    semantic: dict[str, Any] = {
        key: value for key, value in dossier.items() if key != "creado_at"
    }
    for key, default in _DOSSIER_DEFAULTS.items():
        semantic.setdefault(key, default)
    protocol = semantic.get("prueba_discriminante")
    if isinstance(protocol, dict):
        completed = {key: value for key, value in protocol.items() if key != "creado_at"}
        for key, default in _PROTOCOL_DEFAULTS.items():
            completed.setdefault(key, default)
        semantic["prueba_discriminante"] = completed
    return semantic


def _dossier_payload_fingerprint(dossier: Mapping[str, Any]) -> str:
    """Fingerprint the semantic content of a CRIBA dossier for SUPRA.

    The value must equal what SUPRA recomputes from its validated
    ``CribaDossierRequest``; the golden vectors in
    ``tests/integration/test_b01_client_server_agreement.py`` pin both sides.

    Identity follows validated semantics, so a default that was sent explicitly
    and the same default that was omitted are one payload. The optional keys
    above are filled from this module's declared defaults before hashing.
    ``creado_at`` is excluded because it is non-semantic metadata.

    Unicode is deliberately NOT normalized: the dossier travels and is stored as
    given, so folding NFC into NFD would make the fingerprint describe bytes the
    server never received.
    """
    semantic = _with_declared_defaults(dossier)
    raw = json.dumps(
        semantic,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SupraClientError(RuntimeError):
    """Raised when the SUPRA transport or response violates the client contract."""


def objective_from_dossier(dossier: dict[str, Any]) -> str:
    """Map CRIBA's local dossier exchange format onto SUPRA's objective field."""
    prueba = dossier.get("prueba_discriminante") or {}
    fields = [
        ("Problema", dossier.get("problema")),
        ("Hipótesis CRIBA/BLACKFORGE", dossier.get("hipotesis")),
        ("Mecanismo", dossier.get("mecanismo")),
        ("Prueba discriminante", prueba.get("intervencion_prueba")),
        ("Observable", prueba.get("observable")),
        ("Regla de decisión", prueba.get("regla_decision")),
        ("Condición de fracaso", prueba.get("condicion_fracaso")),
    ]
    body = "\n".join(f"{label}: {value}" for label, value in fields if value)
    prefix = (
        "Desarrolla y evalúa este dossier CRIBA/BLACKFORGE sin convertir "
        "evidencia ausente en PASS. "
    )
    return (prefix + body)[:2000]


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


#: Workflow stages that terminate a project. Anything else is nonterminal, and a
#: nonterminal read is a real state the consumer must be able to reconstruct.
_TERMINAL_STAGES = frozenset({"COMPLETED", "BLOCKED", "FAILED"})


def _check_outcome_channels(
    *,
    status: str,
    completion_status: str,
    workflow_status: str,
    stage: str,
    verification_status: str,
    secure_sandbox_status: str,
    require_terminal: bool,
) -> None:
    """Enforce one completion rule for both the write and the read path.

    Reproduced by execution against the real server on 2026-10-02: the write
    path published four separated channels while the read path declared
    ``status: Literal["success"]``. A genuinely BLOCKED project therefore came
    back as ``{"status": "blocked"}`` and the client raised
    ``project lookup violated response contract`` — the client could not
    reconstruct the very state it was built to reconstruct after a restart.
    The rule now lives here once, so the two paths cannot drift apart.

    ``require_terminal`` is True only for POST, which cannot return a
    nonterminal outcome; the read path must be able to describe one.
    """
    completed = (
        status == "success"
        and completion_status == "COMPLETED"
        and workflow_status == "COMPLETED"
        and stage == "COMPLETED"
    )
    blocked = (
        status == "blocked"
        and completion_status == "BLOCKED"
        and workflow_status != "COMPLETED"
        and stage != "COMPLETED"
    )
    failed = status == "error" and stage == "FAILED"
    pending = (
        status == "pending"
        and completion_status == "NOT_COMPLETED"
        and stage not in _TERMINAL_STAGES
    )

    if verification_status in {"FAIL", "NOT_EVALUATED"} and completed:
        raise ValueError(
            "SUPRA contract violation: failed/unevaluated verification cannot be COMPLETED"
        )
    if completed and secure_sandbox_status != "ISOLATED_BOUND_PASS":
        raise ValueError(
            "SUPRA contract violation: COMPLETED requires ISOLATED_BOUND_PASS"
        )
    if completed or blocked or failed or pending:
        return
    if require_terminal:
        raise ValueError("SUPRA contract violation: inconsistent completion fields")
    raise ValueError(
        "SUPRA contract violation: inconsistent completion fields for a persisted read"
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
    secure_sandbox_status: str = "NOT_REPORTED"
    criba_planning_receipt_status: str = "NOT_APPLICABLE"
    criba_mechanism_execution_status: str = "NOT_APPLICABLE"
    idempotent_replay: bool = False
    project_id: str
    stage: str
    posture: dict[str, Any]

    @model_validator(mode="after")
    def reject_contradictory_completion(self) -> "SupraProjectResult":
        _check_outcome_channels(
            status=self.status,
            completion_status=self.completion_status,
            workflow_status=self.workflow_status,
            stage=self.stage,
            verification_status=self.verification_status,
            secure_sandbox_status=self.secure_sandbox_status,
            require_terminal=True,
        )
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


class SupraCribaPlanningReceipt(BaseModel):
    """Typed persisted CRIBA planning receipt returned by SUPRA GET.

    This is deliberately a planning-only record.  Loading a persisted project
    must never promote receipt preservation into execution or validation.
    """

    model_config = ConfigDict(extra="allow")

    receipt_scope: Literal["PLANNED_DISCRIMINANT_PROTOCOL_ONLY"]
    execution_status: Literal["NOT_EXECUTED"]
    scientific_status: Literal["NOT_VALIDATED"]
    criba_dossier_id: str = Field(min_length=1)
    criba_candidate_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    mechanism_version: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    protocol_version: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    integration_version: Literal["criba-supra/1"]
    payload_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_fingerprint: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )


class SupraProjectPostureSnapshot(BaseModel):
    """Typed minimum posture contract needed by CRIBA after restart/reload."""

    model_config = ConfigDict(extra="allow")

    project_id: str = Field(min_length=1)
    stage: Literal[
        "RECEIVED",
        "STRUCTURED",
        "STRATIFIED",
        "RESTRICTED_EXECUTION_VERIFIED",
        "BLOCKED",
        "COMPLETED",
        "FAILED",
    ]
    criba_dossier_receipt: SupraCribaPlanningReceipt | None = None
    final_output: dict[str, Any] | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def reject_contradictory_blocked_snapshot(self) -> "SupraProjectPostureSnapshot":
        if self.stage == "BLOCKED" and (
            self.final_output is not None or self.error_message is not None
        ):
            raise ValueError("BLOCKED posture cannot expose final output or workflow error")
        return self


class SupraProjectLookup(BaseModel):
    """Typed response from GET /api/v1/projects/{project_id}.

    This is the read path a consumer uses to reconstruct state after a restart,
    so it must be able to describe every state the server can persist — not only
    the completed one. ``status`` used to be ``Literal["success"]``, which made
    a genuinely blocked project unreadable through the canonical client: the
    server answered ``{"status": "blocked", ...}`` (measured against the real
    API) and the client refused the response as a contract violation. The
    channels stay separated exactly as on the write path; collapsing them is
    what this model must never do.
    """

    model_config = ConfigDict(extra="allow")

    status: Literal["success", "blocked", "error", "pending"]
    status_scope: str = "WORKFLOW_EXECUTION_ONLY"
    completion_status: Literal["COMPLETED", "BLOCKED", "NOT_COMPLETED"]
    workflow_status: str
    verification_status: str
    scientific_status: str = "NOT_VALIDATED"
    secure_sandbox_status: str = "NOT_REPORTED"
    criba_planning_receipt_status: str = "NOT_APPLICABLE"
    criba_mechanism_execution_status: str = "NOT_APPLICABLE"
    idempotent_replay: bool = False
    status_source: str = "PERSISTED_STATE"
    project_id: str = Field(min_length=1)
    stage: str
    posture: SupraProjectPostureSnapshot

    @model_validator(mode="after")
    def require_matching_project_identity(self) -> "SupraProjectLookup":
        if self.project_id != self.posture.project_id:
            raise ValueError("SUPRA lookup project_id does not match posture project_id")
        if self.stage != self.posture.stage:
            # The summary stage and the persisted stage are two statements about
            # the same fact. If they disagree, a consumer could report the
            # summary's stage while the persisted posture says otherwise.
            raise ValueError("SUPRA lookup stage does not match persisted posture stage")
        _check_outcome_channels(
            status=self.status,
            completion_status=self.completion_status,
            workflow_status=self.workflow_status,
            stage=self.stage,
            verification_status=self.verification_status,
            secure_sandbox_status=self.secure_sandbox_status,
            require_terminal=False,
        )
        if self.status_source != "PERSISTED_STATE":
            raise ValueError(
                "SUPRA lookup must report its state as read from persisted state"
            )
        return self


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

    @staticmethod
    def _validate_response(
        model_type: type[BaseModel],
        payload: dict[str, Any],
        operation: str,
    ) -> BaseModel:
        try:
            return model_type.model_validate(payload)
        except ValidationError as exc:
            raise SupraClientError(
                f"SUPRA {operation} violated response contract"
            ) from exc

    def health(self) -> SupraHealth:
        response = self._client.get("/health")
        self._raise_for_response(response, "health")
        validated = self._validate_response(
            SupraHealth,
            self._json_object(response, "health"),
            "health",
        )
        assert isinstance(validated, SupraHealth)
        return validated

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
        criba_dossier: dict[str, Any] | None = None,
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
        if criba_dossier is not None:
            lineage_fields = (
                "dossier_id", "candidate_id", "claim_id",
                "mechanism_version", "protocol_version",
            )
            if any(
                not isinstance(criba_dossier.get(field), str)
                or not str(criba_dossier.get(field)).strip()
                for field in lineage_fields
            ):
                raise ValueError("CRIBA dossier lineage fields must be non-blank strings")
            canonical_sha256 = re.compile(r"^sha256:[0-9a-f]{64}$")
            for field in ("mechanism_version", "protocol_version"):
                if not canonical_sha256.fullmatch(str(criba_dossier[field])):
                    raise ValueError(f"CRIBA {field} must be canonical sha256:<64 lowercase hex>")
            try:
                fingerprint = _dossier_payload_fingerprint(criba_dossier)
            except (TypeError, ValueError) as exc:
                raise ValueError("CRIBA dossier must be canonical JSON without NaN/Infinity") from exc
            payload["criba_dossier"] = criba_dossier
            payload["criba_integration_version"] = _CRIBA_SUPRA_ENVELOPE_VERSION
            payload["criba_payload_fingerprint"] = fingerprint

        response = self._client.post("/api/v1/projects", json=payload)
        self._raise_for_response(response, "project execution")
        validated = self._validate_response(
            SupraProjectResult,
            self._json_object(response, "project execution"),
            "project execution",
        )
        assert isinstance(validated, SupraProjectResult)
        if criba_dossier is not None:
            receipt = validated.posture.get("criba_dossier_receipt")
            expected = {
                "criba_dossier_id": criba_dossier.get("dossier_id"),
                "criba_candidate_id": criba_dossier.get("candidate_id"),
                "claim_id": criba_dossier.get("claim_id"),
                "mechanism_version": criba_dossier.get("mechanism_version"),
                "protocol_version": criba_dossier.get("protocol_version"),
                "integration_version": _CRIBA_SUPRA_ENVELOPE_VERSION,
                "payload_fingerprint": fingerprint,
            }
            if not isinstance(receipt, dict):
                raise SupraClientError(
                    "SUPRA project execution did not preserve CRIBA dossier lineage"
                )
            if (
                validated.criba_planning_receipt_status != "PRESERVED_NOT_EXECUTED"
                or validated.criba_mechanism_execution_status != "NOT_EXECUTED"
                or receipt.get("receipt_scope") != "PLANNED_DISCRIMINANT_PROTOCOL_ONLY"
                or receipt.get("execution_status") != "NOT_EXECUTED"
                or receipt.get("scientific_status") != "NOT_VALIDATED"
            ):
                raise SupraClientError(
                    "SUPRA project execution promoted a planning receipt beyond its scope"
                )
            if any(receipt.get(key) != value for key, value in expected.items()):
                raise SupraClientError(
                    "SUPRA project execution did not preserve CRIBA dossier lineage"
                )
        return validated

    def get_project(self, project_id: str) -> SupraProjectLookup:
        response = self._client.get(self._project_path(project_id))
        self._raise_for_response(response, "project lookup")
        validated = self._validate_response(
            SupraProjectLookup,
            self._json_object(response, "project lookup"),
            "project lookup",
        )
        assert isinstance(validated, SupraProjectLookup)
        return validated

    def list_projects(self, *, limit: int = 20) -> SupraProjectList:
        if not 1 <= limit <= 50:
            raise ValueError("SUPRA project list limit must be between 1 and 50")
        response = self._client.get("/api/v1/projects", params={"limit": limit})
        self._raise_for_response(response, "project list")
        validated = self._validate_response(
            SupraProjectList,
            self._json_object(response, "project list"),
            "project list",
        )
        assert isinstance(validated, SupraProjectList)
        return validated

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
