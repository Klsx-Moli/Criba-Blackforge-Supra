"""Product orchestration for dossiers. Reuses canonical storage and SupraClient."""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

SCHEMA = "criba-dossier-workflow/1"
EXPORT_SCHEMA = "criba-dossier-recovery-export/1"
IDENTITY = {
    "dossier_id": "criba_dossier_id", "candidate_id": "criba_candidate_id",
    "claim_id": "claim_id", "mechanism_version": "mechanism_version",
    "protocol_version": "protocol_version",
}


class WorkflowError(RuntimeError):
    def __init__(self, code: str, phase: str, message: str, *, project_id: str | None = None,
                 retryable: bool = False, remote_unknown: bool = False) -> None:
        super().__init__(f"{code}: {message}")
        self.code, self.phase, self.project_id = code, phase, project_id
        self.retryable, self.remote_unknown = retryable, remote_unknown

    def diagnostics(self) -> dict[str, Any]:
        cause = self.__cause__
        types: list[str] = []
        status: int | None = None
        for _ in range(5):
            if cause is None:
                break
            types.append(type(cause).__name__)
            response = getattr(cause, "response", None)
            value = getattr(response, "status_code", None)
            if type(value) is int and 100 <= value <= 599:
                status = value
            cause = cause.__cause__
        reason = self.code
        if status in {401, 403}:
            reason = "AUTHORIZATION_ERROR"
        elif status == 429:
            reason = "RATE_LIMIT"
        elif status is not None:
            reason = "HTTP_ERROR"
        elif any("Timeout" in value for value in types):
            reason = "TIMEOUT"
        elif "ValidationError" in types:
            reason = "RESPONSE_SCHEMA_INVALID"
        return {"reason_code": reason, "http_status": status, "cause_types": types}

    def __str__(self) -> str:
        message = super().__str__()
        details = self.diagnostics()
        status = details["http_status"]
        return message + (f" [HTTP {status}: {details['reason_code']}]" if status else "")

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "phase": self.phase, "message": str(self),
                "project_id": self.project_id, "retryable": self.retryable,
                "remote_outcome_unknown": self.remote_unknown, **self.diagnostics(),
                "next_action": "recover same project_id before explicit resubmission"
                if self.remote_unknown else "resolve stated input/dependency"}


@dataclass(frozen=True, slots=True)
class Bindings:
    prepare: Callable[..., dict[str, Any]]
    save: Callable[[dict[str, Any]], Any]
    load: Callable[[str], dict[str, Any] | None]
    fingerprint: Callable[[Mapping[str, Any]], str]
    objective: Callable[[dict[str, Any]], str]
    project_id: Callable[[str], str]


def default_bindings() -> Bindings:
    from .integrations.supra_client import (
        SupraClient,
        _dossier_payload_fingerprint,
        objective_from_dossier,
    )
    from .supra_dossier import cargar_dossier, guardar_dossier, preparar_dossier

    return Bindings(preparar_dossier, guardar_dossier, cargar_dossier,
                    _dossier_payload_fingerprint, objective_from_dossier,
                    SupraClient.validate_project_id)


def new_client() -> Any:
    from .integrations import SupraClient
    return SupraClient()


def dump(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        result = dict(value)
    else:
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            try:
                result = model_dump(mode="json")
            except TypeError:
                result = model_dump()
        elif hasattr(value, "__dict__"):
            result = {k: v for k, v in vars(value).items() if not k.startswith("_")}
        else:
            result = dict(value)
    if not isinstance(result, dict):
        raise WorkflowError("CLIENT_RESULT_INVALID", "read", "Respuesta no estructurada.")
    return copy.deepcopy(result)


def exact(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


@dataclass(slots=True)
class Outcome:
    endpoint: str
    health: dict[str, Any]
    project_id: str | None
    lookup: Any = None
    post: Any = None
    dossier: dict[str, Any] | None = None
    local_status: str = "NO_PROJECTS"
    local_reason: str = "No hay proyectos remotos para recuperar."

    def report(self, projector: Callable[[Any], dict[str, Any]] | None = None) -> dict[str, Any]:
        read = None
        if self.lookup is not None:
            read = projector(self.lookup) if projector else dump(self.lookup)
            read = copy.deepcopy(read)
            if not projector:
                read["receipt"] = read.get("posture", {}).get("criba_dossier_receipt")
            read.update(local_dossier_status=self.local_status, local_dossier_reason=self.local_reason)
        return {"workflow_schema": SCHEMA, "endpoint": self.endpoint,
                "health": copy.deepcopy(self.health), "empty": self.project_id is None,
                "project_id": self.project_id, "post": dump(self.post) if self.post is not None else None,
                "read": read, "dossier": copy.deepcopy(self.dossier),
                "local_dossier_status": self.local_status, "local_dossier_reason": self.local_reason}


class DossierWorkflow:
    def __init__(self, client: Any = None, *, bindings: Bindings | None = None,
                 client_factory: Callable[[], Any] | None = None) -> None:
        self.bindings = bindings or default_bindings()
        self.client = client
        self.owned = client is None
        self.factory = client_factory or new_client

    def http(self) -> Any:
        if self.client is None:
            self.client = self.factory()
        return self.client

    def close(self) -> None:
        if self.owned and self.client is not None:
            self.client.close()
            self.client = None

    def __enter__(self) -> DossierWorkflow:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def validate(self, dossier: Any) -> dict[str, Any]:
        if not isinstance(dossier, dict):
            raise WorkflowError("INVALID_DOSSIER", "input", "Se requiere un dossier JSON.")
        try:
            value: dict[str, Any] = json.loads(json.dumps(dossier, ensure_ascii=False, allow_nan=False))
        except (TypeError, ValueError) as exc:
            raise WorkflowError("INVALID_DOSSIER", "input", "JSON no finito o no serializable.") from exc
        for field in IDENTITY:
            if not exact(value.get(field)):
                raise WorkflowError("INVALID_IDENTITY", "input", field)
        if value.get("estado") != "SUPRA_EJECUCION_PENDIENTE":
            raise WorkflowError("INVALID_LOCAL_STATE", "input", "El protocolo sigue pendiente.")
        self.bindings.fingerprint(value)
        return value

    def prepare(self, entry: dict[str, Any], problem: str) -> dict[str, Any]:
        value = self.validate(self.bindings.prepare(entry, problem))
        self.persist(value)
        return {"workflow_schema": SCHEMA, "dossier": value,
                "local_status": "LOCAL_PRESERVED", "remote_contacted": False}

    def persist(self, value: dict[str, Any]) -> None:
        try:
            self.bindings.save(value)
        except (OSError, ValueError) as exc:
            raise WorkflowError("LOCAL_PERSIST_FAILED", "save", "No se envía sin preservación local.") from exc

    def load_local(self, identity: str) -> dict[str, Any]:
        if not exact(identity):
            raise WorkflowError("INVALID_IDENTITY", "load", "Identidad local no exacta.")
        try:
            value = self.bindings.load(identity)
        except (OSError, ValueError) as exc:
            raise WorkflowError("LOCAL_HISTORY_ERROR", "load", "Historial no legible o ambiguo.") from exc
        if value is None:
            raise WorkflowError("LOCAL_DOSSIER_MISSING", "load", "Dossier no encontrado.")
        return self.validate(value)

    def health(self, client: Any, target: str | None) -> dict[str, Any]:
        try:
            return dump(client.health())
        except Exception as exc:
            raise WorkflowError("SUPRA_UNAVAILABLE", "health", "SUPRA no confirmó disponibilidad.",
                                project_id=target, retryable=True) from exc

    def read(self, client: Any, target: str) -> Any:
        try:
            lookup = client.get_project(target)
        except Exception as exc:
            raise WorkflowError("SUPRA_READ_FAILED", "read", "Estado remoto no confirmado.",
                                project_id=target, retryable=True) from exc
        lookup_project_id = getattr(lookup, "project_id", None)
        if lookup_project_id is None and isinstance(lookup, Mapping):
            lookup_project_id = lookup.get("project_id")
        if lookup_project_id != target:
            raise WorkflowError("REMOTE_PROJECT_MISMATCH", "read", "Respuesta de otro proyecto.",
                                project_id=target)
        return lookup

    def bind_local(self, lookup: Any) -> tuple[dict[str, Any] | None, str, str]:
        posture = getattr(lookup, "posture", None)
        if posture is None and isinstance(lookup, Mapping):
            posture = lookup.get("posture")
        if isinstance(posture, Mapping):
            receipt = posture.get("criba_dossier_receipt")
        else:
            receipt = getattr(posture, "criba_dossier_receipt", None)
        if receipt is not None and not isinstance(receipt, (dict, Mapping)):
            # Stubs/tests may wrap the receipt in an object exposing model_dump.
            model_dump = getattr(receipt, "model_dump", None)
            if callable(model_dump):
                try:
                    receipt = model_dump(mode="json")
                except TypeError:
                    receipt = model_dump()
        if not isinstance(receipt, dict):
            return None, "RECEIPT_NOT_PRESENT", "Sin receipt CRIBA preservado."
        if (receipt.get("receipt_scope") != "PLANNED_DISCRIMINANT_PROTOCOL_ONLY"
                or receipt.get("integration_version") != "criba-supra/1"
                or receipt.get("execution_status") != "NOT_EXECUTED"
                or receipt.get("scientific_status") != "NOT_VALIDATED"):
            return None, "RECEIPT_SCOPE_MISMATCH", "Receipt fuera del alcance de planificación."
        if any(not exact(receipt.get(remote)) for remote in IDENTITY.values()):
            return None, "RECEIPT_IDENTITY_INVALID", "Receipt con identidad no exacta."
        try:
            local = self.bindings.load(receipt["criba_dossier_id"])
        except (OSError, ValueError):
            return None, "LOCAL_HISTORY_ERROR", "Historial no legible o ambiguo."
        if local is None:
            return None, "LOCAL_DOSSIER_MISSING", "El dossier del receipt no existe localmente."
        if any(not exact(local.get(field)) or local[field] != receipt[remote]
               for field, remote in IDENTITY.items()):
            return None, "IDENTITY_MISMATCH", "Dossier y receipt tienen identidad distinta."
        if local.get("estado") != "SUPRA_EJECUCION_PENDIENTE":
            return None, "LOCAL_STATE_MISMATCH", "Estado local no compatible con planificación."
        try:
            fingerprint = self.bindings.fingerprint(local)
        except (TypeError, ValueError):
            return None, "LOCAL_PAYLOAD_INVALID", "Payload local fuera de contrato."
        if fingerprint != receipt.get("payload_fingerprint"):
            return None, "PAYLOAD_MISMATCH", "Contenido local distinto del receipt."
        return copy.deepcopy(local), "LOCAL_DOSSIER_RECOVERED", "Dossier vinculado y recuperado."

    def outcome(self, client: Any, health: dict[str, Any], target: str,
                lookup: Any, post: Any = None) -> Outcome:
        local, code, reason = self.bind_local(lookup)
        return Outcome(str(client.config.endpoint), health, target, lookup, post, local, code, reason)

    def submit(self, dossier: dict[str, Any], project_id: str | None = None, *,
               use_model: bool = False, provider: str | None = None, model: str | None = None,
               domain: str = "criba_blackforge", allow_disruptive: bool = True,
               objective: str | None = None) -> Outcome:
        value = self.validate(dossier)
        target = project_id or "astram2-" + hashlib.sha256(value["dossier_id"].encode()).hexdigest()[:32]
        target = self.bindings.project_id(target)
        self.persist(value)
        client = self.http()
        health = self.health(client, target)
        kwargs: dict[str, Any] = {
            "objective": objective if objective is not None else self.bindings.objective(value),
            "project_id": target, "criba_dossier": value, "use_model": use_model,
            "domain": domain, "allow_disruptive": allow_disruptive,
        }
        if provider is not None:
            kwargs["provider"] = provider
        if model is not None:
            kwargs["model"] = model
        try:
            post = client.run_project(**kwargs)
        except ValueError as exc:
            raise WorkflowError("INVALID_CLIENT_INPUT", "client_input", "El cliente rechazó la entrada.",
                                project_id=target) from exc
        except Exception as exc:
            raise WorkflowError("SUBMIT_UNCONFIRMED", "submit", "Recupera el mismo ID antes de reintentar.",
                                project_id=target, retryable=True, remote_unknown=True) from exc
        if dump(post).get("project_id") != target:
            raise WorkflowError("REMOTE_PROJECT_MISMATCH", "submit", "POST confirmó otro proyecto.",
                                project_id=target, remote_unknown=True)
        try:
            lookup = self.read(client, target)
        except WorkflowError as exc:
            exc.remote_unknown = True
            raise
        result = self.outcome(client, health, target, lookup, post)
        if result.dossier is None:
            raise WorkflowError("POST_READBACK_UNCONFIRMED", "bind", result.local_reason,
                                project_id=target, remote_unknown=True)
        return result

    def recover(self, project_id: str) -> Outcome:
        target = self.bindings.project_id(project_id)
        client = self.http()
        return self.outcome(client, self.health(client, target), target, self.read(client, target))

    def recover_latest(self, limit: int = 20) -> Outcome:
        client = self.http()
        health = self.health(client, None)
        try:
            projects = dump(client.list_projects(limit=limit)).get("projects")
        except Exception as exc:
            raise WorkflowError("LIST_FAILED", "list", "Listado remoto no confirmado.", retryable=True) from exc
        if not isinstance(projects, list):
            raise WorkflowError("INVALID_PROJECT_LIST", "list", "Listado no estructurado.")
        if not projects:
            return Outcome(str(client.config.endpoint), health, None)
        first = projects[0]
        if not isinstance(first, dict) or not exact(first.get("project_id")):
            raise WorkflowError("INVALID_PROJECT_LIST", "list", "Identidad no exacta en el listado.")
        target = self.bindings.project_id(first["project_id"])
        return self.outcome(client, health, target, self.read(client, target))

    def export_bundle(self, project_id: str) -> dict[str, Any]:
        result = self.recover(project_id)
        if result.dossier is None:
            raise WorkflowError("NO_LOCAL_EXPORT", "export", result.local_reason, project_id=project_id)
        read = dump(result.lookup)
        return {"format": EXPORT_SCHEMA, "scope": "PLANNED_PROTOCOL_ONLY",
                "project_id": result.project_id, "dossier": result.dossier,
                "receipt": read["posture"]["criba_dossier_receipt"], "remote_snapshot": read,
                "snapshot_is_live_authority_after_import": False}

    def import_bundle(self, package: dict[str, Any]) -> dict[str, Any]:
        if (not isinstance(package, dict) or package.get("format") != EXPORT_SCHEMA
                or package.get("scope") != "PLANNED_PROTOCOL_ONLY"):
            raise WorkflowError("INVALID_EXPORT", "import", "Formato no soportado.")
        value = self.validate(package.get("dossier"))
        receipt = package.get("receipt")
        if not isinstance(receipt, dict) or any(receipt.get(remote) != value[field]
                                              for field, remote in IDENTITY.items()):
            raise WorkflowError("INVALID_EXPORT_IDENTITY", "import", "Receipt y dossier incompatibles.")
        if (receipt.get("receipt_scope") != "PLANNED_DISCRIMINANT_PROTOCOL_ONLY"
                or receipt.get("integration_version") != "criba-supra/1"
                or receipt.get("execution_status") != "NOT_EXECUTED"
                or receipt.get("scientific_status") != "NOT_VALIDATED"
                or receipt.get("payload_fingerprint") != self.bindings.fingerprint(value)):
            raise WorkflowError("INVALID_EXPORT_RECEIPT", "import", "Contenido/scope incompatible.")
        self.persist(value)
        return {"workflow_schema": SCHEMA, "status": "LOCAL_IMPORTED_REMOTE_UNVERIFIED",
                "dossier_id": value["dossier_id"], "remote_contacted": False,
                "scientific_status": "NOT_VALIDATED"}
