"""Offline K3 receipt reader, not evidence or an inference-budget authority.

A closed reservation alone cannot validate its response. The host supplies a
frozen S1 context and the original receipt envelope; the persisted digest,
identity and structured semantic reading must all agree. S0 is deliberately
unsupported until its baseline mapping is specified. Old rows remain readable
metadata, never silently upgraded to an accepted reading.

The gate's legacy physical_calls field is a 0/1 *accepted receipt proxy*, not
observed transport calls. An error/absence can hide a consumed call. No phase
may be authorized using this proxy; a separate transport journal is required.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from benchmarks.innovation.semantic_lab import Trial, direct_request, read_current

ETIQUETAS = frozenset({"SUPPORT", "REJECT", "UNRESOLVED"})
OUTCOMES = frozenset({*ETIQUETAS, "ERROR", "NOT_RUN"})
CAMPOS = ("case_id", "repetition", "arm", "outcome", "physical_calls")
Slot = tuple[str, int, str]


@dataclass(frozen=True)
class SlotContext:
    """Expected S1 identity from the host plan, never from a model callback."""

    trial: Trial
    repetition: int
    reviewer: str
    attempt_nonce: str

    @property
    def attempt(self) -> str:
        # Bind arm/repetition through the existing Request.attempt field,
        # without introducing a second request digest algorithm.
        if type(self.repetition) is not int or self.repetition not in range(3):
            raise ValueError("invalid repetition")
        if not isinstance(self.attempt_nonce, str) or not self.attempt_nonce.strip():
            raise ValueError("invalid attempt nonce")
        return f"S1:{self.repetition}:{self.attempt_nonce}"

    @property
    def slot(self) -> Slot:
        return self.trial.case_id, self.repetition, "S1"

    @property
    def request_sha256(self) -> str:
        return direct_request(self.trial, self.reviewer, self.attempt).sha256


def _registro(slot: Slot, outcome: str, receipt_proxy: int = 0) -> dict[str, Any]:
    return dict(zip(CAMPOS, (*slot, outcome, receipt_proxy), strict=True))


def normalizar_slot(
    *,
    case_id: str,
    repetition: int,
    arm: str,
    estado_reserva: Mapping[str, Any] | None,
    recibos: Sequence[Mapping[str, Any]] | None = None,
    contexto: SlotContext | None = None,
    raw_receipt: str | None = None,
) -> dict[str, Any]:
    """Read a coherent snapshot from Storage.load_semantic_snapshot (K3).

    The input context and original envelope are separate host-owned inputs.
    Do not infer a verdict from labels or a body attached to ledger metadata.
    The legacy body_sha256 column identifies the *whole canonical envelope*
    for a review, not its request or just the inner body. No DB migration.
    """
    slot = (case_id, repetition, arm)
    error = _registro(slot, "ERROR")
    rows = recibos if recibos is not None else ()
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return error
    if estado_reserva is None:
        return error if rows or raw_receipt is not None else _registro(slot, "NOT_RUN")
    if not isinstance(estado_reserva, Mapping):
        return error
    status = estado_reserva.get("status")
    if status == "ACTIVE":
        # Without a transport journal we cannot distinguish never sent from
        # interrupted. NOT_RUN here means no closed receipt, NOT zero usage.
        if estado_reserva.get("receipt_sha256") is None and not rows and raw_receipt is None:
            return _registro(slot, "NOT_RUN")
        return error
    if status != "CLOSED" or not isinstance(contexto, SlotContext):
        return error
    if raw_receipt is None:
        return error
    try:
        if contexto.slot != slot or type(repetition) is not int or repetition not in range(3):
            return error
        if type(contexto.repetition) is not int or not isinstance(contexto.trial, Trial):
            return error
        scope, attempt, request = (
            contexto.trial.scope, contexto.attempt, contexto.request_sha256
        )
        if (
            estado_reserva.get("scope") != scope
            or estado_reserva.get("attempt") != attempt
            or estado_reserva.get("reviewer") != contexto.reviewer
            or estado_reserva.get("request_sha256") != request
            or not estado_reserva.get("closed_at")
        ):
            return error
        receipt = estado_reserva.get("receipt_sha256")
        if not isinstance(receipt, str) or len(receipt) != 64:
            return error
        if any(
            not isinstance(row, Mapping)
            or row.get("scope") != scope
            or row.get("attempt") != attempt
            for row in rows
        ):
            return error
        matches = [row for row in rows if row.get("body_sha256") == receipt]
        if len(matches) != 1:
            return error
        match = matches[0]
        # ACTIVE is the actual status-at-insertion of the winning receipt.
        # STALE cannot become current even if other identity fields match.
        if match.get("status") != "ACTIVE" or match.get("request_sha256") != request:
            return error
        reading = read_current(
            contexto.trial, reviewer=contexto.reviewer, attempt=attempt,
            current_request_sha256=request, raw=raw_receipt,
        )
        if reading.request_sha256 != request or reading.receipt_sha256 != receipt:
            return error
        outcome = {
            "REVIEW_SUPPORTED": "SUPPORT",
            "REVIEW_REJECTED": "REJECT",
            "REVIEW_UNRESOLVED": "UNRESOLVED",
        }.get(reading.outcome)
        if outcome is None:
            return error
        return _registro(slot, outcome, 1)
    except (AttributeError, KeyError, TypeError, ValueError, RecursionError, OverflowError):
        return error


def normalizar_lote(
    slots: Iterable[Slot],
    estado_por_slot: Mapping[Slot, Mapping[str, Any] | None],
    recibos_por_slot: Mapping[Slot, Sequence[Mapping[str, Any]]] | None = None,
    *,
    contextos_por_slot: Mapping[Slot, SlotContext] | None = None,
    raw_por_slot: Mapping[Slot, str] | None = None,
) -> list[dict[str, Any]]:
    """Keep all planned slots, with no reuse of a request across repetitions."""
    recibos_por_slot = recibos_por_slot or {}
    contextos_por_slot = contextos_por_slot or {}
    raw_por_slot = raw_por_slot or {}
    salida: list[dict[str, Any]] = []
    seen: set[str] = set()
    for case_id, repetition, arm in slots:
        key = (case_id, repetition, arm)
        context = contextos_por_slot.get(key)
        registro = normalizar_slot(
            case_id=case_id, repetition=repetition, arm=arm,
            estado_reserva=estado_por_slot.get(key), recibos=recibos_por_slot.get(key),
            contexto=context, raw_receipt=raw_por_slot.get(key),
        )
        if registro["outcome"] in ETIQUETAS and context is not None:
            request = context.request_sha256
            if request in seen:
                raise ValueError("review request reused across slots")
            seen.add(request)
        salida.append(registro)
    return salida


def validar_registros(registros: Sequence[Mapping[str, Any]]) -> list[str]:
    """Validate the legacy five-field shape, not provenance or consumption."""
    errores: list[str] = []
    vistos: set[Slot] = set()
    for i, r in enumerate(registros):
        if not isinstance(r, Mapping) or set(r) != set(CAMPOS):
            errores.append(f"[{i}] campos invalidos")
            continue
        case_id, repetition, arm = r["case_id"], r["repetition"], r["arm"]
        if (not isinstance(case_id, str) or not case_id.strip()
                or type(repetition) is not int or repetition not in range(3)
                or not isinstance(arm, str) or arm not in ("S0", "S1")):
            errores.append(f"[{i}] identidad de slot invalida")
            continue
        slot = (case_id, repetition, arm)
        if slot in vistos:
            errores.append(f"[{i}] slot duplicado {slot}")
        vistos.add(slot)
        outcome, calls = r["outcome"], r["physical_calls"]
        if not isinstance(outcome, str) or outcome not in OUTCOMES:
            errores.append(f"[{i}] outcome invalido {outcome!r}")
            continue
        if type(calls) is not int or calls not in (0, 1):
            errores.append(f"[{i}] physical_calls invalido {calls!r}")
            continue
        if outcome == "NOT_RUN" and calls != 0:
            errores.append(f"[{i}] NOT_RUN con {calls} llamadas")
        if outcome in ETIQUETAS and calls != 1:
            errores.append(f"[{i}] {outcome} con {calls} llamadas")
    return errores
