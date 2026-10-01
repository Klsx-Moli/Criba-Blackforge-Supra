"""FastAPI backend for the provider-neutral SUPRA Agentic Taskmaster."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .dossier import export_full_html_dossier
from .mcp_handler import handle_mcp_jsonrpc_request
from .models import current_authoritative_execution
from .providers import ProviderError, get_provider, provider_names
from .runner import TaskmasterRunner, taskmaster_runner
from .state import DuplicateProjectError, ProjectStateLoadError, state_manager

logger = logging.getLogger("supra_agentic.service")
MAX_MCP_BODY_SIZE = 8 * 1024 * 1024
MAX_API_BODY_SIZE = 8 * 1024 * 1024
_BOUNDED_JSON_PATHS = {"/api/v1/projects", "/api/v1/generate"}
_LOOPBACK_CLIENTS = {"127.0.0.1", "::1", "testclient"}


def _require_mutation_authority(request: Request) -> None:
    """Require bearer auth when configured; otherwise permit loopback only.

    SUPRA is local-first. An unset token is not an open network mode: mutation
    endpoints remain available only to loopback clients. Network deployments
    must configure SUPRA_API_TOKEN and send ``Authorization: Bearer <token>``.
    """
    configured = os.getenv("SUPRA_API_TOKEN")
    if configured is not None and configured != "":
        authorization = request.headers.get("authorization", "")
        scheme, separator, supplied = authorization.partition(" ")
        if (
            separator != " "
            or scheme.lower() != "bearer"
            or not supplied
            or not secrets.compare_digest(supplied, configured)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mutation authorization required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return

    require_auth = bool(os.getenv("K_SERVICE")) or os.getenv(
        "SUPRA_REQUIRE_AUTH", ""
    ).strip().lower() in {"1", "true", "yes", "on"}
    if require_auth:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mutation authorization is not configured.",
        )

    client_host = request.client.host if request.client is not None else None
    if client_host not in _LOOPBACK_CLIENTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mutation endpoints require loopback access or SUPRA_API_TOKEN.",
        )


def _parse_cors_origins(raw: str | None) -> list[str]:
    """Parse explicit CORS origins; absent configuration remains closed."""
    if raw is None or not raw.strip():
        return []
    origins = [item.strip() for item in raw.split(",")]
    if any(not item for item in origins):
        raise RuntimeError("SUPRA_CORS_ORIGINS contains an empty origin")
    for origin in origins:
        if origin == "*":
            raise RuntimeError("SUPRA_CORS_ORIGINS requires explicit origins; wildcard is forbidden")
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(f"Invalid CORS origin: {origin!r}")
    return origins


CORS_ORIGINS = _parse_cors_origins(os.getenv("SUPRA_CORS_ORIGINS"))

app = FastAPI(
    title="SUPRA Agentic Taskmaster",
    version="1.0.0",
    description="Provider-neutral task decomposition, scoped strategy-coverage evaluation, restricted execution telemetry, and evidence generation.",
)


@app.exception_handler(ProjectStateLoadError)
async def _handle_project_state_load_error(
    _request: Request, exc: ProjectStateLoadError
) -> JSONResponse:
    """Do not degrade corrupt persisted authority into a false 404."""
    logger.error(
        "Persisted project state is corrupt or incompatible: %s (%s)",
        exc.project_id,
        exc.error_type,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Persisted project state is corrupt or incompatible."},
    )


class _BoundedJsonBodyMiddleware:
    """Bound expensive JSON endpoints before framework body parsing."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path") not in _BOUNDED_JSON_PATHS
        ):
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        if raw_length is not None:
            try:
                declared_size = int(raw_length)
            except ValueError:
                await self._reject(send, 400, "Invalid Content-Length header")
                return
            if declared_size < 0:
                await self._reject(send, 400, "Invalid Content-Length header")
                return
            if declared_size > MAX_API_BODY_SIZE:
                await self._reject(send, 413, "Request body too large")
                return

        chunks: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                await self.app(scope, receive, send)
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > MAX_API_BODY_SIZE:
                await self._reject(send, 413, "Request body too large")
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        sent = False

        async def replay_receive() -> dict[str, Any]:
            nonlocal sent
            if sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(send: Any, status_code: int, detail: str) -> None:
        body = json.dumps({"detail": detail}, separators=(",", ":")).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        })
        await send({"type": "http.response.body", "body": body})


app.add_middleware(_BoundedJsonBodyMiddleware)

# Enable CORS - configurable, default restrictive (empty list = no CORS)
if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

STATIC_DIR = Path(__file__).parent / "web"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class CribaDiscriminantProtocolRequest(BaseModel):
    """Discriminant protocol prepared by CRIBA; receipt is not execution evidence."""

    model_config = ConfigDict(extra="forbid")
    afirmacion_decisiva: str = Field(..., min_length=1, max_length=600)
    alternativa_explicativa: str = Field(..., min_length=1, max_length=1200)
    intervencion_prueba: str = Field(..., min_length=1, max_length=600)
    observable: str = Field(..., min_length=1, max_length=400)
    comparacion: str = Field("", max_length=800)
    metrica: str = Field("", max_length=400)
    resultado_favorable_mecanismo: str = Field(..., min_length=1, max_length=400)
    resultado_favorable_alternativa: str = Field(..., min_length=1, max_length=400)
    regla_decision: str = Field(..., min_length=1, max_length=400)
    condicion_fracaso: str = Field(..., min_length=1, max_length=400)
    coste_permisos: str = Field("", max_length=400)
    estado_prueba: Literal["NO_EJECUTADA"] = "NO_EJECUTADA"


_CRIBA_SUPRA_ENVELOPE_VERSION = "criba-supra/1"


def _criba_payload_fingerprint(dossier: CribaDossierRequest) -> str:
    semantic = dossier.model_dump(exclude_unset=True)
    semantic.pop("creado_at", None)
    raw = json.dumps(semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CribaDossierRequest(BaseModel):
    """Versioned CRIBA planning payload accepted by the project endpoint."""

    model_config = ConfigDict(extra="forbid")
    dossier_id: str = Field(..., min_length=1, max_length=128)
    candidate_id: str = Field(..., min_length=1, max_length=256)
    run_id: str = Field("", max_length=256)
    claim_id: str = Field(..., min_length=1, max_length=256)
    protocol_version: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    mechanism_version: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    problema: str = Field(..., min_length=1, max_length=400)
    bloqueo: str = Field("", max_length=1200)
    origen_bloqueo: str = Field("", max_length=120)
    hipotesis: str = Field(..., min_length=1, max_length=800)
    mecanismo: str = Field(..., min_length=1, max_length=2000)
    evidence_delivered: list[Any] = Field(default_factory=list)
    evidence_documented_as_used: list[Any] = Field(default_factory=list)
    evidencia_utilizada: list[Any] = Field(default_factory=list)
    prueba_discriminante: CribaDiscriminantProtocolRequest
    supuestos: list[Any] = Field(default_factory=list)
    estado: Literal["SUPRA_EJECUCION_PENDIENTE"]
    creado_at: str = Field("", max_length=80)


def _criba_dossier_receipt(
    dossier: CribaDossierRequest,
    *,
    integration_version: str,
    payload_fingerprint: str,
    request_fingerprint: str,
) -> dict[str, Any]:
    """Flatten only the discriminant planning facts SUPRA needs to preserve."""
    protocol = dossier.prueba_discriminante
    return {
        "receipt_scope": "PLANNED_DISCRIMINANT_PROTOCOL_ONLY",
        "execution_status": "NOT_EXECUTED",
        "scientific_status": "NOT_VALIDATED",
        "integration_version": integration_version,
        "payload_fingerprint": payload_fingerprint,
        "request_fingerprint": request_fingerprint,
        "criba_dossier_id": dossier.dossier_id,
        "criba_candidate_id": dossier.candidate_id,
        "claim_id": dossier.claim_id,
        "mechanism_version": dossier.mechanism_version,
        "protocol_version": dossier.protocol_version,
        "alternativa_explicativa": protocol.alternativa_explicativa,
        "intervencion_prueba": protocol.intervencion_prueba,
        "observable": protocol.observable,
        "resultado_favorable_mecanismo": protocol.resultado_favorable_mecanismo,
        "resultado_favorable_alternativa": protocol.resultado_favorable_alternativa,
        "regla_decision": protocol.regla_decision,
        "condicion_fracaso": protocol.condicion_fracaso,
    }


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str = Field(
        ..., min_length=5, max_length=2000, description="The challenge or problem to solve."
    )
    domain: str = Field("general", max_length=100, description="Target problem domain.")
    project_id: str | None = Field(
        None,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
        description="Optional storage-safe custom project ID.",
    )
    allow_disruptive: bool = Field(
        True, description="Whether to include disruptive divergent pathways."
    )
    provider: str | None = Field(
        None, max_length=64, description="Provider name, or SUPRA_PROVIDER when omitted."
    )
    model: str | None = Field(
        None, max_length=200, description="Provider model ID; auto-discovered when omitted."
    )
    use_model: bool = Field(
        False, description="Add optional model assistance without replacing deterministic gates."
    )
    criba_dossier: CribaDossierRequest | None = Field(
        None,
        description=(
            "Optional CRIBA planning dossier. SUPRA preserves a receipt but does not "
            "treat receipt as execution or scientific validation."
        ),
    )
    criba_integration_version: Literal["criba-supra/1"] | None = None
    criba_payload_fingerprint: str | None = Field(None, pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_criba_envelope(self) -> CreateProjectRequest:
        if self.criba_dossier is None:
            if self.criba_integration_version is not None or self.criba_payload_fingerprint is not None:
                raise ValueError("CRIBA envelope metadata requires criba_dossier")
            return self
        if self.criba_integration_version != _CRIBA_SUPRA_ENVELOPE_VERSION:
            raise ValueError("unsupported CRIBA integration version")
        expected = _criba_payload_fingerprint(self.criba_dossier)
        if self.criba_payload_fingerprint != expected:
            raise ValueError("CRIBA payload fingerprint mismatch")
        return self


def _criba_request_fingerprint(req: CreateProjectRequest) -> str:
    """Fingerprint execution-affecting request fields for safe retry recognition.

    The dossier itself is represented by its independently verified semantic
    fingerprint.  A caller cannot change objective/provider/model/flags under
    the same project ID and have that request mistaken for a lost-response
    retry.
    """
    payload = {
        "project_id": req.project_id,
        "objective": req.objective.strip(),
        "domain": req.domain,
        "allow_disruptive": req.allow_disruptive,
        "provider": req.provider,
        "model": req.model,
        "use_model": req.use_model,
        "criba_integration_version": req.criba_integration_version,
        "criba_payload_fingerprint": req.criba_payload_fingerprint,
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _project_execution_payload(
    posture: Any, *, idempotent_replay: bool = False
) -> dict[str, Any]:
    """Serialize the canonical workflow outcome for create and safe replay."""
    if posture.stage.value not in {"BLOCKED", "COMPLETED"}:
        raise ValueError("project execution payload requires a terminal non-failed posture")
    final_output = posture.final_output or {}
    is_blocked = posture.stage.value == "BLOCKED"
    latest_execution = current_authoritative_execution(posture)
    secure_sandbox_status = (
        "RESTRICTED_BOUND_PASS_NOT_ISOLATED"
        if latest_execution and latest_execution.passed and latest_execution.identity_bound
        else "NOT_REPORTED"
    )
    return {
        "status": "blocked" if is_blocked else "success",
        "status_scope": "WORKFLOW_EXECUTION_ONLY",
        "completion_status": "BLOCKED" if is_blocked else "COMPLETED",
        "workflow_status": posture.stage.value,
        "verification_status": (
            posture.verification.verdict if posture.verification else "NOT_EVALUATED"
        ),
        "verification_scope": (
            posture.verification.verification_scope
            if posture.verification
            else "TEXTUAL_STRATEGY_COVERAGE"
        ),
        "scientific_status": final_output.get("scientific_status", "NOT_VALIDATED"),
        "secure_sandbox_status": secure_sandbox_status,
        "criba_planning_receipt_status": (
            "PRESERVED_NOT_EXECUTED" if posture.criba_dossier_receipt else "NOT_APPLICABLE"
        ),
        "criba_mechanism_execution_status": (
            "NOT_EXECUTED" if posture.criba_dossier_receipt else "NOT_APPLICABLE"
        ),
        "idempotent_replay": idempotent_replay,
        "project_id": posture.project_id,
        "stage": posture.stage.value,
        "posture": posture.model_dump(),
    }


def _failed_project_response(posture: Any, *, idempotent_replay: bool) -> Response:
    """Return the stable failed-workflow envelope without leaking internal error text."""
    return Response(
        content=json.dumps(
            {
                "status": "error",
                "status_scope": "WORKFLOW_EXECUTION",
                "project_id": posture.project_id,
                "stage": "FAILED",
                "error": "Pipeline execution failed",
                "verification": posture.verification.model_dump()
                if posture.verification
                else None,
                "idempotent_replay": idempotent_replay,
            }
        ),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        media_type="application/json",
    )


def _is_exact_criba_retry(req: CreateProjectRequest, existing: Any) -> bool:
    """Return true only for the exact persisted CRIBA request contract."""
    if req.criba_dossier is None:
        return False
    receipt = existing.criba_dossier_receipt
    return bool(
        isinstance(receipt, dict)
        and receipt.get("integration_version") == req.criba_integration_version
        and receipt.get("payload_fingerprint") == req.criba_payload_fingerprint
        and receipt.get("request_fingerprint") == _criba_request_fingerprint(req)
    )


def _idempotent_replay_response(req: CreateProjectRequest) -> Response | None:
    """Resolve a known project before any provider/workflow side effects."""
    if req.project_id is None:
        return None
    existing = state_manager.get_project(req.project_id)
    if existing is None:
        return None
    if not _is_exact_criba_retry(req, existing):
        raise HTTPException(status_code=409, detail="project_id already exists.")
    if existing.stage.value == "FAILED":
        return _failed_project_response(existing, idempotent_replay=True)
    if existing.stage.value not in {"BLOCKED", "COMPLETED"}:
        raise HTTPException(
            status_code=409,
            detail="existing project is nonterminal; automatic replay unsafe.",
        )
    return Response(
        content=json.dumps(_project_execution_payload(existing, idempotent_replay=True)),
        status_code=status.HTTP_200_OK,
        media_type="application/json",
    )


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(..., min_length=1, max_length=12000)
    provider: str | None = Field(None, max_length=64)
    model: str | None = Field(None, max_length=200)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=32768)


@app.get("/health", tags=["System"])
def healthcheck() -> dict[str, Any]:
    """Health probe with non-secret provider metadata."""
    return {
        "status": "healthy",
        "service": "supra-agentic-taskmaster",
        "version": "1.0.0",
        "provider": taskmaster_runner.provider_metadata(),
        "storage": {
            "mode": state_manager.storage_mode,
            "durability": (
                "instance-only"
                if state_manager.storage_mode == "INSTANCE_EPHEMERAL"
                else "depends-on-configured-filesystem"
                if state_manager.storage_mode == "CONFIGURED_FILESYSTEM"
                else "local-host"
            ),
        },
        "webmcp_enabled": True,
    }


@app.get("/api/v1/providers", tags=["Providers"])
def list_provider_options() -> dict[str, Any]:
    """List supported providers and safe local configuration metadata."""
    providers: list[dict[str, Any]] = []
    for name in provider_names():
        try:
            provider = get_provider(name)
            metadata = provider.metadata()
            metadata["alias"] = name != provider.name
            providers.append(metadata)
        except ValueError as exc:
            providers.append(
                {
                    "name": name,
                    "configured": False,
                    "error": "provider_configuration_invalid",
                    "error_type": type(exc).__name__,
                }
            )
    return {
        "status": "success",
        "active": os.getenv("SUPRA_PROVIDER", "hermes").strip().lower(),
        "providers": providers,
    }


@app.get("/", response_class=HTMLResponse, tags=["UI"])
def serve_ui() -> Response:
    """Serve the primary Web UI."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse(
            "<h1>SUPRA Agentic Taskmaster API Online</h1><p>Static UI building...</p>"
        )
    return FileResponse(str(index_file))


@app.post(
    "/api/v1/projects",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    tags=["Taskmaster"],
)
def create_and_run_project(req: CreateProjectRequest, request: Request) -> dict[str, Any] | Response:
    """Execute the five-stage workflow with deterministic gates.

    Returns HTTP status for workflow execution. A 201 response means the
    workflow request completed; verification and scientific status are returned
    separately and must not be inferred from HTTP success.
    - 201 Created + {"status": "success"} on workflow completion
    - 500 Internal Server Error + {"status": "error"} on workflow failure
    """
    _require_mutation_authority(request)
    replay = _idempotent_replay_response(req)
    if replay is not None:
        return replay
    try:
        runner = TaskmasterRunner(provider_name=req.provider, model_name=req.model)
        posture = runner.run_golden_path(
            objective=req.objective,
            project_id=req.project_id,
            domain=req.domain,
            allow_disruptive=req.allow_disruptive,
            use_model=req.use_model,
            criba_dossier_receipt=(
                _criba_dossier_receipt(
                    req.criba_dossier,
                    integration_version=req.criba_integration_version or "",
                    payload_fingerprint=req.criba_payload_fingerprint or "",
                    request_fingerprint=_criba_request_fingerprint(req),
                )
                if req.criba_dossier is not None
                else None
            ),
        )

        # Workflow failure and strategy-coverage verdict are different
        # channels. A coverage FAIL is returned as verification state; it is not
        # converted into an execution/server failure.
        if posture.stage.value == "FAILED":
            return _failed_project_response(posture, idempotent_replay=False)

        return _project_execution_payload(posture)
    except DuplicateProjectError as exc:
        if req.project_id is not None and req.criba_dossier is not None:
            existing = state_manager.get_project(req.project_id)
            if existing is not None and _is_exact_criba_retry(req, existing):
                if existing.stage.value == "FAILED":
                    return _failed_project_response(existing, idempotent_replay=True)
                if existing.stage.value not in {"BLOCKED", "COMPLETED"}:
                    raise HTTPException(
                        status_code=409,
                        detail="existing project is nonterminal; automatic replay unsafe.",
                    ) from exc
                return Response(
                    content=json.dumps(
                        _project_execution_payload(existing, idempotent_replay=True)
                    ),
                    status_code=status.HTTP_200_OK,
                    media_type="application/json",
                )
        raise HTTPException(status_code=409, detail="project_id already exists.") from exc
    except Exception as exc:
        logger.error("Project execution failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Project execution failed.") from exc


@app.post("/api/v1/generate", tags=["Providers"])
def generate_with_provider(req: GenerateRequest, request: Request) -> dict[str, Any]:
    """Generate model output through the selected provider boundary."""
    _require_mutation_authority(request)
    try:
        runner = TaskmasterRunner(provider_name=req.provider, model_name=req.model)
        response = runner.generate(
            req.prompt,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except ProviderError as exc:
        logger.error("Provider generation failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Provider request failed.") from exc
    except ValueError as exc:
        logger.error("Invalid provider request (%s)", type(exc).__name__)
        raise HTTPException(status_code=400, detail="Invalid provider request.") from exc
    return {
        "status": "success",
        "provider": response.provider,
        "model": response.model,
        "text": response.text,
        "tool_calls": response.tool_calls,
    }


@app.get("/api/v1/projects", tags=["Taskmaster"])
def list_projects(limit: int = 20) -> dict[str, Any]:
    """List recent Taskmaster projects."""
    projects = state_manager.list_projects(limit=limit)
    return {
        "status": "success",
        "count": len(projects),
        "projects": [p.model_dump() for p in projects],
        "storage_errors": state_manager.last_list_load_errors,
    }


@app.get("/api/v1/projects/{project_id}", tags=["Taskmaster"])
def get_project_posture(project_id: str) -> dict[str, Any]:
    """Retrieve full project telemetry and deliverable ledger."""
    posture = state_manager.get_project(project_id)
    if not posture:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return {
        "status": "success",
        "project_id": posture.project_id,
        "posture": posture.model_dump(),
    }


# Compat alias: the live Cloud Run deployment and all submission docs
# reference /api/v1/demo/quick-run. Keep it working alongside the new
# /api/v1/examples/quick-run route.
@app.post("/api/v1/demo/quick-run", tags=["Examples"], include_in_schema=False)
def demo_quick_run_alias(request: Request) -> dict[str, Any]:
    """Backwards-compatible alias for the historical demo URL."""
    return example_quick_run(request)


@app.post("/api/v1/examples/quick-run", tags=["Examples"])
def example_quick_run(request: Request) -> dict[str, Any]:
    """Run a deterministic example without contacting a model provider."""
    _require_mutation_authority(request)
    demo_objective = (
        "Design an autonomous secretless service mesh with real-time continuous "
        "invariant verification and automated counterfactual rollback."
    )
    posture = taskmaster_runner.run_golden_path(
        objective=demo_objective,
        project_id="example-quick-run",
        domain="cloud_security",
        allow_disruptive=True,
    )
    return {
        "status": "success",
        "example": True,
        "stages_completed": 5 if posture.stage.value == "COMPLETED" else 4,
        "workflow_status": posture.stage.value,
        "verification_status": (
            posture.verification.verdict if posture.verification else "NOT_EVALUATED"
        ),
        "scientific_status": (
            (posture.final_output or {}).get("scientific_status", "NOT_VALIDATED")
        ),
        "project_id": posture.project_id,
        "stage": posture.stage.value,
        "deliverable": posture.final_output,
        "posture": posture.model_dump(),
    }


@app.post("/api/v1/mcp", tags=["WebMCP"])
async def mcp_jsonrpc_endpoint(request: Request) -> dict[str, Any]:
    """Native WebMCP JSON-RPC 2.0 Protocol Handler.

    Includes body size limit (8 MiB) and basic JSON-RPC argument validation.
    """
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header") from exc
        if declared_size < 0:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header")
        if declared_size > MAX_MCP_BODY_SIZE:
            raise HTTPException(status_code=413, detail="Request body too large (max 8 MiB)")

    body = await request.body()
    if len(body) > MAX_MCP_BODY_SIZE:
        raise HTTPException(status_code=413, detail="Request body too large (max 8 MiB)")
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

    # Basic JSON-RPC 2.0 validation
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON-RPC payload must be an object")
    if payload.get("jsonrpc") != "2.0":
        raise HTTPException(status_code=400, detail="Only JSON-RPC 2.0 is supported")
    if "method" not in payload:
        raise HTTPException(status_code=400, detail="Missing 'method' in JSON-RPC request")
    if "id" not in payload:
        raise HTTPException(status_code=400, detail="Missing 'id' in JSON-RPC request")

    if payload.get("method") == "tools/call":
        _require_mutation_authority(request)

    return handle_mcp_jsonrpc_request(payload)


@app.get("/api/v1/export/dossier/{project_id}", tags=["Export"])
def export_technical_dossier(project_id: str) -> dict[str, Any]:
    """Export a markdown technical dossier of the completed project."""
    posture = state_manager.get_project(project_id)
    if not posture:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    decomp = posture.decomposition
    cand = posture.selected_candidate
    ver = posture.verification
    out = posture.final_output
    confidence_text = f"{ver.confidence_score:.2f}" if ver else "N/A"
    verification_text = ver.verdict if ver else "NOT_EVALUATED"
    verification_scope = ver.verification_scope if ver else "TEXTUAL_STRATEGY_COVERAGE"
    h0_text = out.get("null_hypothesis_h0", "NOT_SPECIFIED") if out else "NOT_SPECIFIED"
    h0_status = out.get("h0_evaluation_status", "NOT_EVALUATED") if out else "NOT_EVALUATED"
    scientific_status = out.get("scientific_status", "NOT_VALIDATED") if out else "NOT_VALIDATED"

    md_lines = [
        f"# TECHNICAL DOSSIER: {posture.objective}",
        f"**Project ID:** `{posture.project_id}`  ",
        f"**Stage:** `{posture.stage.value}`  ",
        f"**Audit SHA-256:** `{out.get('audit_sha256', 'N/A') if out else 'N/A'}`  ",
        "",
        "---",
        "",
        "## 1. Problem Decomposition & Invariants",
        f"- **Domain:** {decomp.domain if decomp else 'N/A'}",
        f"- **Core Objective:** {decomp.core_objective if decomp else 'N/A'}",
        "### System Invariants (Must Hold):",
    ]
    if decomp:
        for inv in decomp.invariants:
            md_lines.append(f"- [x] {inv}")
        md_lines.append("")
        md_lines.append("### Mutable Assumptions (Challenged):")
        for mut in decomp.mutable_assumptions:
            md_lines.append(f"- [ ] ~{mut}~")

    md_lines.extend(
        [
            "",
            "## 2. Selected Strategy Pathway",
            f"- **Pathway:** {cand.pathway_name if cand else 'N/A'}",
            f"- **Paradigm:** `{cand.paradigm_type if cand else 'N/A'}`",
            f"- **Hypothesis:** {cand.hypothesis if cand else 'N/A'}",
            f"- **Feasibility:** {cand.feasibility_score if cand else 0.0:.2f} | **Divergence:** {cand.divergence_score if cand else 0.0:.2f}",
            "",
            "## 3. Strategy Coverage & Restricted Execution Telemetry",
            f"- **Coverage Verdict:** `{verification_text}` (Coverage fraction: {confidence_text})",
            f"- **Scope:** `{verification_scope}`",
            f"- **Rationale:** {ver.rationale if ver else 'No coverage evaluation available.'}",
            "",
            "## 4. Empirical Falsification (H0)",
            f"- **Null Hypothesis:** `{h0_text}`",
            f"- **H0 Evaluation Status:** `{h0_status}`",
            f"- **Scientific Status:** `{scientific_status}`",
            "",
            "## 5. Checkpoints Timeline",
        ]
    )
    for chk in posture.checkpoints:
        md_lines.append(
            f"- **[{chk.stage.value}]** `{chk.actor}`: {chk.title} — *{chk.evidence_summary}*"
        )

    return {
        "status": "success",
        "project_id": project_id,
        "markdown_dossier": "\n".join(md_lines),
    }


@app.get("/api/v1/export/dossier/html/{project_id}", response_class=HTMLResponse, tags=["Export"])
def export_html_dossier_route(project_id: str) -> HTMLResponse:
    """Export a self-contained HTML specification with embedded SVG architecture."""
    posture = state_manager.get_project(project_id)
    if not posture:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    html_content = export_full_html_dossier(posture)
    return HTMLResponse(html_content)
