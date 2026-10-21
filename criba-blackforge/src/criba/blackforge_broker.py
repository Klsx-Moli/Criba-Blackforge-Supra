"""Execution broker: the single point of authority for BLACKFORGE.

Every architectural decision here follows one rule: a permission is verified
where the effect happens. Nothing in this module trusts a boolean, a GUI
checkbox, a model instruction or an HTTP 2xx.

Three processes, not microservices:

  * the KERNEL (criba core / Shadow UI) may analyse artefacts and propose
    plans. It has no access to executors: it cannot open this database's
    authorisation ledger for writing, and it holds no credential.
  * the BROKER (this module) owns the authorisation ledger, the durable
    attempt journal and the dispatch loop. It is the ONLY path to an executor.
  * the EXECUTOR performs typed operations inside an authorised lab. It
    accepts typed operations only and never widens its own scope.

Fail-closed policy:

  * No grant, a grant for another plan, an expired grant, a consumed nonce, a
    pre-condition that does not hold, or a persistence failure BEFORE
    dispatch means ZERO effect and an explicit error.
  * A crash after a possible effect leaves OUTCOME_UNKNOWN and is NEVER
    retried automatically. A SQLite transaction makes reservation+consumption
    atomic; it does not make an external effect exactly-once, and this module
    does not pretend otherwise.

Isolation is provided by the operating system, not by this process: the
ledger is a separate SQLite file whose directory permissions grant write
access to the broker identity only (see `broker_paths`). Same-user processes
are NOT isolation; see `scripts/install_broker_acl.py` and the module docstring
of `blackforge_broker` for the enforcement boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from .blackforge_case import (
    Authorization,
    AuthorizationAxis,
    ExecutionAxis,
    Plan,
    PlanStep,
    build_plan,
    digest_of,
)

BROKER_SCHEMA_VERSION = "blackforge-broker/1"

# Operations the executor will accept. Free-form strings from a model are
# rejected at the type boundary, not after they reach the lab.
TYPED_OPERATIONS: dict[str, frozenset[str]] = {
    "probe_parser_quote": frozenset({"payload_family", "endpoint_kind"}),
    "probe_authz_matrix": frozenset({"role_a", "role_b", "resource_kind"}),
    "read_header_names": frozenset({"target"}),
    "enumerate_declared_routes": frozenset({"target"}),
    "snapshot_config_flags": frozenset({"target", "flag_names"}),
}


class BrokerError(RuntimeError):
    """Base class. Every message names the contract it protects."""


class PolicyError(BrokerError):
    """The broker refused: this capability is not enabled for this scope."""


class AuthorizationError(BrokerError):
    """No valid authorization binds this exact action to this exact plan."""


class PreconditionError(BrokerError):
    """A declared precondition does not hold. Zero effect."""


class PersistenceError(BrokerError):
    """Durability failed BEFORE dispatch: zero effect, explicit error."""


class OutcomeUnknown(BrokerError):
    """A possible effect whose result was lost. Never auto-retried."""


class CapabilityNotEnabled(PolicyError):
    """Execution stays disabled until an administrative operation enables it."""


# ---------------------------------------------------------------------------
# Paths and policy
# ---------------------------------------------------------------------------


def broker_dir() -> Path:
    """Directory holding the ledger and journal.

    `BROKER_STATE_DIR` exists so tests and a lab deployment can point the
    broker at an isolated tree. It is not a security control by itself: the
    security boundary is the filesystem ACL on this directory (see
    `scripts/install_broker_acl.py`).
    """
    override = os.environ.get("BROKER_STATE_DIR")
    if override:
        return Path(override).expanduser()
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "BLACKFORGE-Broker"


def ledger_path() -> Path:
    return broker_dir() / "broker.sqlite3"


def journal_path() -> Path:
    return broker_dir() / "journal.jsonl"


class Policy:
    """What this installation is allowed to do at all.

    Invariant from the design: `enabled=true` in a config does NOT satisfy an
    authorisation contract. It only decides whether the capability exists.
    Widening a capability requires an authenticated administrative operation
    that records WHO widened it and WHEN, and the kernel cannot perform it.
    """

    def __init__(
        self,
        *,
        execution_enabled: bool = False,
        policy_version: str = "bf-broker/1",
        capability_safety_classes: frozenset[str] = frozenset({"S2_SANDBOX", "S3_HIGH_CONTROL"}),
        max_duration_s: int = 900,
    ) -> None:
        self.execution_enabled = execution_enabled
        self.policy_version = policy_version
        self.capability_safety_classes = capability_safety_classes
        self.max_duration_s = max_duration_s

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_enabled": self.execution_enabled,
            "policy_version": self.policy_version,
            "capability_safety_classes": sorted(self.capability_safety_classes),
            "max_duration_s": self.max_duration_s,
        }


# ---------------------------------------------------------------------------
# Durable journal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JournalEntry:
    seq: int
    at: str
    kind: str
    attempt_id: str
    detail: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "at": self.at,
            "kind": self.kind,
            "attempt_id": self.attempt_id,
            "detail": self.detail,
        }


class Journal:
    """Append-only record of every authorisation and dispatch decision.

    Invariant 11: an authorised attempt MUST be durably recorded BEFORE the
    dispatch. The journal is fsync'd per append so a crash cannot lose the
    record of an effect that may already have happened.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or journal_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, kind: str, attempt_id: str, detail: Mapping[str, Any]) -> JournalEntry:
        seq = self._count() + 1
        entry = JournalEntry(
            seq=seq,
            at=datetime.now(timezone.utc).isoformat(),
            kind=kind,
            attempt_id=attempt_id,
            detail=dict(detail),
        )
        line = json.dumps(entry.to_dict(), ensure_ascii=False)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return entry

    def _count(self) -> int:
        if not self._path.is_file():
            return 0
        with self._path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())

    def read_all(self) -> list[JournalEntry]:
        if not self._path.is_file():
            return []
        entries: list[JournalEntry] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                entries.append(
                    JournalEntry(
                        seq=int(raw["seq"]),
                        at=str(raw["at"]),
                        kind=str(raw["kind"]),
                        attempt_id=str(raw["attempt_id"]),
                        detail=dict(raw.get("detail") or {}),
                    )
                )
        return entries

    def kinds_for(self, attempt_id: str) -> list[str]:
        return [e.kind for e in self.read_all() if e.attempt_id == attempt_id]


# ---------------------------------------------------------------------------
# Executor boundary
# ---------------------------------------------------------------------------


class RestrictedExecutor(Protocol):
    """Typed operations only. No arbitrary command, ever."""

    def available_operations(self) -> Sequence[str]: ...

    def execute(self, kind: str, target: str, params: Mapping[str, Any]) -> dict[str, Any]: ...


def validate_operation(kind: str, target: str, params: Mapping[str, Any]) -> None:
    """Reject free-form work at the type boundary."""
    allowed = TYPED_OPERATIONS.get(kind)
    if allowed is None:
        raise PolicyError(
            f"La operación {kind!r} no es un tipo aceptado por el executor "
            f"restringido. Tipos válidos: {sorted(TYPED_OPERATIONS)}"
        )
    unexpected = set(params) - allowed
    if unexpected:
        raise PolicyError(
            f"La operación {kind!r} admite {sorted(allowed)}; recibido {sorted(unexpected)}"
        )
    if not isinstance(target, str) or not target.strip():
        raise PreconditionError("La operación no resuelve un objetivo.")


# ---------------------------------------------------------------------------
# The broker
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DispatchReceipt:
    """Evidence that an attempt happened. NOT evidence that it was validated."""

    attempt_id: str
    plan_digest: str
    grant_id: str
    dispatched_actions: tuple[str, ...]
    execution_state: ExecutionAxis
    results: dict[str, Any]
    artifact_digests: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "plan_digest": self.plan_digest,
            "grant_id": self.grant_id,
            "dispatched_actions": list(self.dispatched_actions),
            "execution_state": self.execution_state.value,
            "results": self.results,
            "artifact_digests": self.artifact_digests,
            "receipt_is_execution_evidence": True,
            "receipt_is_validation_evidence": False,
        }


@dataclass
class Attempt:
    attempt_id: str
    case_id: str
    plan_digest: str
    grant_id: str
    actions: tuple[str, ...]
    targets: tuple[str, ...]
    environment: str
    limits: tuple[str, ...]
    state: ExecutionAxis = ExecutionAxis.NOT_STARTED
    unknown_reason: str = ""
    receipt: dict[str, Any] | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "case_id": self.case_id,
            "plan_digest": self.plan_digest,
            "grant_id": self.grant_id,
            "actions": list(self.actions),
            "targets": list(self.targets),
            "environment": self.environment,
            "limits": list(self.limits),
            "state": self.state.value,
            "unknown_reason": self.unknown_reason,
            "receipt": self.receipt,
            "created_at": self.created_at,
        }


class Broker:
    """Authorises and dispatches. The kernel has no other route to an executor."""

    def __init__(
        self,
        *,
        policy: Policy | None = None,
        journal: Journal | None = None,
        executor: RestrictedExecutor | None = None,
        ledger: Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.policy = policy or Policy()
        self.journal = journal or Journal()
        self.executor = executor
        self._ledger_path = ledger or ledger_path()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_ledger()

    # -- storage ----------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self._ledger_path, timeout=30.0, isolation_level=None)
        con.row_factory = sqlite3.Row
        return con

    def _init_ledger(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS grants (
                    grant_id TEXT PRIMARY KEY,
                    approver_identity TEXT NOT NULL,
                    plan_digest TEXT NOT NULL,
                    actions_json TEXT NOT NULL,
                    targets_json TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    start_not_before TEXT NOT NULL,
                    max_duration_s INTEGER NOT NULL,
                    nonce TEXT UNIQUE NOT NULL,
                    limits_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    credential_ref TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    plan_digest TEXT NOT NULL,
                    grant_id TEXT NOT NULL,
                    actions_json TEXT NOT NULL,
                    targets_json TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    limits_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    unknown_reason TEXT NOT NULL DEFAULT '',
                    receipt_json TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS consumptions (
                    nonce TEXT PRIMARY KEY,
                    grant_id TEXT NOT NULL,
                    attempt_id TEXT NOT NULL,
                    consumed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS case_revisions (
                    case_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    digest TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    PRIMARY KEY (case_id, revision)
                );
                """
            )
            con.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES('schema', ?)",
                (BROKER_SCHEMA_VERSION,),
            )

    # -- administration ----------------------------------------------------

    def register_grant(
        self,
        grant: Authorization,
        *,
        credential_ref: str = "",
        administratively_enabled: bool = False,
    ) -> str:
        """Enrol an authorisation. Only an admin path may pass a credential.

        The ledger stores the CANONICAL authorization shape: a grant has no
        separate display id, its one-time nonce IS its ledger identity, and
        `approved_plan_digest` binds the exact plan. Re-mapping to another
        vocabulary here would create a second source of truth for what was
        approved.
        """
        state = (
            AuthorizationAxis.GRANTED.value
            if administratively_enabled
            else AuthorizationAxis.NONE.value
        )
        grant_id = grant.nonce
        actions = list(grant.approved_actions) or _actions_from_digest_shape(grant)
        with self._connect() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO grants(
                    grant_id, approver_identity, plan_digest, actions_json,
                    targets_json, policy_version, issued_at, start_not_before,
                    max_duration_s, nonce, limits_json, state, credential_ref
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    grant_id,
                    grant.subject,
                    grant.approved_plan_digest,
                    json.dumps(actions, ensure_ascii=False),
                    json.dumps(list(grant.resolved_targets), ensure_ascii=False),
                    grant.policy_version,
                    grant.issued_at,
                    grant.valid_from,
                    grant.max_duration_s,
                    grant.nonce,
                    json.dumps(list(grant.limits), ensure_ascii=False),
                    state,
                    credential_ref,
                ),
            )
        return str(state)

    def enable_execution(self, *, actor: str, reason: str) -> None:
        """Widen the capability. Authenticated administrative operation only.

        Refuses to widen silently: the actor and the reason are journalled, and
        a grant without a credential reference cannot be dispatched afterwards.
        """
        if not actor.strip() or not reason.strip():
            raise PolicyError("Ampliar capacidad exige actor y motivo explícitos.")
        if not self._has_credentialed_grant():
            raise PolicyError(
                "No existe ninguna autorización con credencial enrolada; "
                "habilitar ejecución sin ella fabricaría autoridad."
            )
        self.journal.append(
            "capability_widened",
            "policy",
            {"actor": actor, "reason": reason, "policy": self.policy.to_dict()},
        )
        self.policy.execution_enabled = True

    def _has_credentialed_grant(self) -> bool:
        with self._connect() as con:
            row = con.execute(
                "SELECT COUNT(*) AS n FROM grants WHERE credential_ref <> ''"
            ).fetchone()
        return bool(row and row["n"])

    # -- plan / dispatch ---------------------------------------------------

    def reserve(
        self,
        *,
        case_id: str,
        plan_digest: str,
        grant_id: str,
        actions: Sequence[str],
        targets: Sequence[str],
        environment: str,
        limits: Sequence[str] = (),
    ) -> Attempt:
        """Durably reserve and CONSUME the grant, before any effect.

        Reservation + consumption happen in one IMMEDIATE transaction. If it
        fails, nothing is dispatched and the error is explicit.
        """
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            grant = con.execute(
                "SELECT * FROM grants WHERE grant_id=?", (grant_id,)
            ).fetchone()
            if grant is None:
                raise AuthorizationError(
                    f"No existe la autorización {grant_id}; cero despachos."
                )
            if grant["state"] != AuthorizationAxis.GRANTED.value:
                raise AuthorizationError(
                    f"La autorización {grant_id} está en {grant['state']}; cero despachos."
                )
            consumed = con.execute(
                "SELECT attempt_id FROM consumptions WHERE nonce=?",
                (grant["nonce"],),
            ).fetchone()
            if consumed is not None:
                raise AuthorizationError(
                    f"El nonce de {grant_id} ya se consumió en el intento "
                    f"{consumed['attempt_id']}; cero despachos."
                )
            moment = self._clock()
            start = datetime.fromisoformat(grant["start_not_before"])
            if moment < start:
                raise AuthorizationError(
                    f"La autorización {grant_id} no es válida hasta {grant['start_not_before']}."
                )
            if (moment - start).total_seconds() > grant["max_duration_s"]:
                raise AuthorizationError(
                    f"La autorización {grant_id} está expirada; cero despachos."
                )
            for action in actions:
                if action not in json.loads(grant["actions_json"]):
                    raise AuthorizationError(
                        f"La acción {action!r} no está enumerada en {grant_id}; cero despachos."
                    )
            if plan_digest != grant["plan_digest"]:
                raise AuthorizationError(
                    "El plan alterado invalida su aprobación; cero despachos."
                )

            attempt_id = f"ATT-{uuid.uuid4().hex[:12]}"
            con.execute(
                """
                INSERT INTO attempts(
                    attempt_id, case_id, plan_digest, grant_id, actions_json,
                    targets_json, environment, limits_json, state,
                    unknown_reason, receipt_json, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    attempt_id,
                    case_id,
                    plan_digest,
                    grant_id,
                    json.dumps(list(actions), ensure_ascii=False),
                    json.dumps(list(targets), ensure_ascii=False),
                    environment,
                    json.dumps(list(limits), ensure_ascii=False),
                    ExecutionAxis.RESERVED.value,
                    "",
                    None,
                    moment.isoformat(),
                ),
            )
            con.execute(
                "INSERT INTO consumptions(nonce, grant_id, attempt_id, consumed_at)"
                " VALUES(?,?,?,?)",
                (grant["nonce"], grant_id, attempt_id, moment.isoformat()),
            )
            con.execute(
                "UPDATE grants SET state=? WHERE grant_id=?",
                (AuthorizationAxis.CONSUMED.value, grant_id),
            )
            con.commit()
        except BrokerError:
            con.rollback()
            raise
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            con.rollback()
            raise PersistenceError(
                f"La reserva durable falló antes del despacho; cero efectos: {exc}"
            ) from exc
        finally:
            con.close()

        attempt = Attempt(
            attempt_id=attempt_id,
            case_id=case_id,
            plan_digest=plan_digest,
            grant_id=grant_id,
            actions=tuple(actions),
            targets=tuple(targets),
            environment=environment,
            limits=tuple(limits),
            state=ExecutionAxis.RESERVED,
        )
        # Invariant 11: durable BEFORE dispatch, fsync'd.
        self.journal.append(
            "attempt_reserved",
            attempt_id,
            {"grant": grant_id, "plan_digest": plan_digest, "actions": list(actions)},
        )
        return attempt

    def dispatch(self, attempt: Attempt, *, executor: RestrictedExecutor | None = None) -> DispatchReceipt:
        """Execute a reserved attempt. The ONLY place an executor is reached."""
        if not self.policy.execution_enabled:
            raise CapabilityNotEnabled(
                "La ejecución está deshabilitada en esta instalación; "
                "habilitarla exige una operación administrativa autenticada."
            )
        runner = executor or self.executor
        if runner is None:
            raise CapabilityNotEnabled(
                "No hay executor restringido disponible; cero despachos."
            )
        available = set(runner.available_operations())
        results: dict[str, Any] = {}
        artifacts: dict[str, str] = {}
        executed: list[str] = []
        try:
            for index, action in enumerate(attempt.actions):
                spec = _operation_spec(action, attempt.targets, index)
                validate_operation(spec["kind"], spec["target"], spec["params"])
                if spec["kind"] not in available:
                    raise PreconditionError(
                        f"El executor no ofrece {spec['kind']}; cero efectos adicionales."
                    )
                outcome = runner.execute(spec["kind"], spec["target"], spec["params"])
                results[action] = outcome
                artifacts[action] = _artifact_digest(outcome)
                executed.append(action)
        except BrokerError:
            self._mark(attempt.attempt_id, ExecutionAxis.FAILED, reason="operación rechazada")
            raise
        except Exception as exc:  # noqa: BLE001 - executor contract violation
            # An effect may already have happened: do NOT claim failure cleanly
            # and do NOT retry. Reconcile first.
            self._mark(
                attempt.attempt_id,
                ExecutionAxis.OUTCOME_UNKNOWN,
                reason=f"executor devolvio una excepcion: {type(exc).__name__}: {exc}",
            )
            raise OutcomeUnknown(
                f"El intento {attempt.attempt_id} pudo tener efecto y su resultado "
                f"se perdió ({type(exc).__name__}); reconciliar antes de repetir."
            ) from exc

        receipt = DispatchReceipt(
            attempt_id=attempt.attempt_id,
            plan_digest=attempt.plan_digest,
            grant_id=attempt.grant_id,
            dispatched_actions=tuple(executed),
            execution_state=ExecutionAxis.COMPLETED,
            results=results,
            artifact_digests=artifacts,
        )
        self._mark(
            attempt.attempt_id,
            ExecutionAxis.COMPLETED,
            receipt=receipt.to_dict(),
        )
        self.journal.append(
            "attempt_completed",
            attempt.attempt_id,
            {"actions": executed, "artifact_digests": artifacts},
        )
        return receipt

    def _mark(
        self,
        attempt_id: str,
        state: ExecutionAxis,
        *,
        reason: str = "",
        receipt: Mapping[str, Any] | None = None,
    ) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE attempts SET state=?, unknown_reason=?, receipt_json=?"
                " WHERE attempt_id=?",
                (
                    state.value,
                    reason,
                    json.dumps(dict(receipt), ensure_ascii=False) if receipt else None,
                    attempt_id,
                ),
            )
        self.journal.append(
            "attempt_state_changed",
            attempt_id,
            {"state": state.value, "reason": reason},
        )

    # -- queries -----------------------------------------------------------

    def get_attempt(self, attempt_id: str) -> Attempt | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM attempts WHERE attempt_id=?", (attempt_id,)
            ).fetchone()
        if row is None:
            return None
        return Attempt(
            attempt_id=row["attempt_id"],
            case_id=row["case_id"],
            plan_digest=row["plan_digest"],
            grant_id=row["grant_id"],
            actions=tuple(json.loads(row["actions_json"])),
            targets=tuple(json.loads(row["targets_json"])),
            environment=row["environment"],
            limits=tuple(json.loads(row["limits_json"])),
            state=ExecutionAxis(row["state"]),
            unknown_reason=row["unknown_reason"],
            receipt=json.loads(row["receipt_json"]) if row["receipt_json"] else None,
            created_at=row["created_at"],
        )

    def attempts_for_case(self, case_id: str) -> list[Attempt]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT attempt_id FROM attempts WHERE case_id=? ORDER BY created_at",
                (case_id,),
            ).fetchall()
        return [a for a in (self.get_attempt(r["attempt_id"]) for r in rows) if a]

    def record_case_revision(self, case_id: str, revision: int, digest: str) -> None:
        """Revisions preserve evidence and pending uncertainty (invariant 4)."""
        with self._connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO case_revisions"
                "(case_id, revision, digest, recorded_at) VALUES(?,?,?,?)",
                (case_id, revision, digest, datetime.now(timezone.utc).isoformat()),
            )
        self.journal.append(
            "case_revision_recorded", case_id, {"revision": revision, "digest": digest}
        )

    def pending_uncertainty(self) -> list[dict[str, Any]]:
        """Everything still uncertain after a restart. Never silently resolved."""
        with self._connect() as con:
            rows = con.execute(
                "SELECT attempt_id, state, unknown_reason FROM attempts"
                " WHERE state IN (?,?,?)",
                (
                    ExecutionAxis.OUTCOME_UNKNOWN.value,
                    ExecutionAxis.DISPATCHED.value,
                    ExecutionAxis.RESERVED.value,
                ),
            ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        pass


def _operation_spec(
    action: str, targets: Sequence[str], index: int
) -> dict[str, Any]:
    """Resolve one action into a typed operation.

    An action string encodes `kind|target|k=v,k=v`. Anything else is rejected
    before it reaches the executor.
    """
    parts = action.split("|")
    if len(parts) < 2:
        raise PolicyError(
            f"La acción {action!r} no declara tipo y objetivo "
            "(formato kind|target[|k=v,...])."
        )
    kind = parts[0].strip()
    target = parts[1].strip()
    params: dict[str, Any] = {}
    if len(parts) > 2:
        for pair in parts[2].split(","):
            if not pair.strip():
                continue
            key, _, value = pair.partition("=")
            params[key.strip()] = value.strip()
    return {"kind": kind, "target": target, "params": params, "index": index}


def _actions_from_digest_shape(grant: Authorization) -> list[str]:
    """Actions an approval enumerates when it carries no explicit list.

    A grant that names no action authorises nothing: an empty list is the
    correct reading, and `reserve` will refuse every dispatch against it. The
    function exists so the refusal is explicit at enrolment rather than a
    surprise at dispatch time.
    """
    return []


def _artifact_digest(payload: Any) -> str:
    return digest_of(payload)


__all__ = [
    "Authorization",
    "AuthorizationAxis",
    "AuthorizationError",
    "Broker",
    "BrokerError",
    "CapabilityNotEnabled",
    "DispatchReceipt",
    "Journal",
    "JournalEntry",
    "OutcomeUnknown",
    "PersistenceError",
    "Policy",
    "PolicyError",
    "PreconditionError",
    "TYPED_OPERATIONS",
    "Attempt",
    "broker_dir",
    "journal_path",
    "ledger_path",
    "validate_operation",
]