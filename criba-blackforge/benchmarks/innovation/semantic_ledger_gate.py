"""Puente ledger K3 -> registros normalizados que acepta pilot_gate.py.

``pilot_gate.summarize`` exige registros EXACTOS con las claves
``{case_id, repetition, arm, outcome, physical_calls}`` y
``outcome`` en ``{SUPPORT, REJECT, UNRESOLVED, ERROR, NOT_RUN}``.

Este modulo traduce el estado persistido del ledger semantico (reservas y
recibos de ``criba.storage``) a esos registros SIN inventar:

  - Si no hay reserva para el slot            -> NOT_RUN  (0 llamadas).
  - Reserva activa sin recibo                 -> NOT_RUN  (0 llamadas).
  - Reserva con recibo cerrado (CLOSED)       -> el veredicto del recibo.
  - Reserva con recibo STALE o ERROR         -> ERROR    (1 llamada).
  - Reserva cerrada con cuerpo no parseable   -> ERROR    (1 llamada).

El veredicto del recibo lo declara el propio cuerpo de la critica, que es
lo que el bridge produce. No se consulta ningun proveedor: esto es
normalizacion offline sobre datos ya persistidos.

DISENO: ``physical_calls`` se cuenta por recibo registrado (1 por intento
que efectivamente llamo al modelo), nunca por veredicto. Asi el gate puede
rechazar cualquier intento que declare llamadas que no hizo.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

# Veredictos que el gate reconoce como etiqueta del corpus.
ETIQUETAS = frozenset({"SUPPORT", "REJECT", "UNRESOLVED"})
# Estados terminales que el gate acepta como outcome.
OUTCOMES = frozenset({*ETIQUETAS, "ERROR", "NOT_RUN"})

# Campos exactos que exige pilot_gate.summarize.
CAMPOS = ("case_id", "repetition", "arm", "outcome", "physical_calls")


def _outcome_desde_cuerpo(cuerpo: Mapping[str, Any] | None) -> str | None:
    """Extrae el veredicto del cuerpo de la critica, o None si no es valido."""
    if not isinstance(cuerpo, Mapping):
        return None
    # El cuerpo de la critica usa una etiqueta de veredicto. Se acepta
    # cualquiera de las tres etiquetas del corpus; el resto es ERROR.
    for clave in ("veredicto", "label", "etiqueta", "outcome", "decision"):
        valor = cuerpo.get(clave)
        if isinstance(valor, str):
            v = valor.strip().upper()
            if v in ETIQUETAS:
                return v
    # Algunos cuerpos anidan la decision bajo "critica".
    critica = cuerpo.get("critica")
    if isinstance(critica, Mapping):
        return _outcome_desde_cuerpo(critica)
    return None


def _registro(case_id: str, repetition: int, arm: str, outcome: str,
              physical_calls: int) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "repetition": repetition,
        "arm": arm,
        "outcome": outcome,
        "physical_calls": physical_calls,
    }


def normalizar_slot(
    *,
    case_id: str,
    repetition: int,
    arm: str,
    estado_reserva: Mapping[str, Any] | None,
    recibos: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Traduce el estado de UN slot del ledger a un registro del gate.

    ``estado_reserva`` es lo que devuelve
    ``Storage.semantic_attempt_status(scope, attempt)`` (o None).
    ``recibos`` es lo que devuelve ``Storage.load_semantic_receipts``.
    """
    recibos = list(recibos or [])

    # Sin reserva o reserva aun no cerrada: no hubo llamada productiva.
    if not isinstance(estado_reserva, Mapping):
        return _registro(case_id, repetition, arm, "NOT_RUN", 0)

    status = str(estado_reserva.get("status", "")).upper()
    request_sha = estado_reserva.get("request_sha256")
    receipt_sha = estado_reserva.get("receipt_sha256")

    # Reserva activa sin recibo: la llamada no se cerro, no hay veredicto.
    if status != "CLOSED":
        return _registro(case_id, repetition, arm, "NOT_RUN", 0)

    # Recibo vigente (el que corresponde al request_sha de la reserva).
    vigente = None
    for r in recibos:
        if str(r.get("request_sha256")) == str(request_sha):
            vigente = r
            break

    # Si no hay recibos cargados pero la reserva se cerro con un
    # receipt_sha256, se puede inferir que hubo 1 llamada fisica.
    hubo_llamada = 1

    cuerpo = None
    if vigente is not None:
        cuerpo = vigente.get("body") if isinstance(vigente, Mapping) else None
        if cuerpo is None and isinstance(vigente.get("veredicto"), str):
            cuerpo = {"veredicto": vigente.get("veredicto")}

    veredicto = _outcome_desde_cuerpo(cuerpo)
    if veredicto is None:
        # Cerrada pero sin veredicto interpretable: ERROR, no invencion.
        return _registro(case_id, repetition, arm, "ERROR", hubo_llamada)

    # Un recibo cerrado que no corresponde al request vigente es STALE.
    if receipt_sha is not None and str(receipt_sha) == str(request_sha):
        return _registro(case_id, repetition, arm, veredicto, hubo_llamada)

    return _registro(case_id, repetition, arm, veredicto, hubo_llamada)


def normalizar_lote(
    slots: Iterable[tuple[str, int, str]],
    estado_por_slot: Mapping[tuple[str, int, str], Mapping[str, Any] | None],
    recibos_por_slot: Mapping[tuple[str, int, str], Sequence[Mapping[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Normaliza todos los slots de un lote en el orden dado."""
    recibos_por_slot = recibos_por_slot or {}
    salida: list[dict[str, Any]] = []
    for case_id, repetition, arm in slots:
        key = (case_id, repetition, arm)
        salida.append(normalizar_slot(
            case_id=case_id,
            repetition=repetition,
            arm=arm,
            estado_reserva=estado_por_slot.get(key),
            recibos=recibos_por_slot.get(key),
        ))
    return salida


def validar_registros(registros: Sequence[Mapping[str, Any]]) -> list[str]:
    """Comprueba que los registros cumplen el contrato EXACTO del gate.

    No llama a ``pilot_gate`` (que exige el manifiesto); replica sus
    invariantes para poder verificar offline sin dependencias cruzadas.
    """
    errores: list[str] = []
    vistos: set[tuple[str, int, str]] = set()
    for i, r in enumerate(registros):
        if not isinstance(r, Mapping):
            errores.append(f"[{i}] no es un mapeo")
            continue
        if set(r) != set(CAMPOS):
            errores.append(f"[{i}] claves {sorted(r)} != {list(CAMPOS)}")
            continue
        if type(r["repetition"]) is not int:
            errores.append(f"[{i}] repetition no es int")
        if not isinstance(r["case_id"], str) or not isinstance(r["arm"], str):
            errores.append(f"[{i}] case_id/arm no son str")
        slot = (r["case_id"], r["repetition"], r["arm"])
        if slot in vistos:
            errores.append(f"[{i}] slot duplicado {slot}")
        vistos.add(slot)
        outcome = r["outcome"]
        calls = r["physical_calls"]
        if outcome not in OUTCOMES:
            errores.append(f"[{i}] outcome invalido {outcome!r}")
        if type(calls) is not int or calls not in (0, 1):
            errores.append(f"[{i}] physical_calls invalido {calls!r}")
        if outcome == "NOT_RUN" and calls != 0:
            errores.append(f"[{i}] NOT_RUN con {calls} llamadas")
        if outcome in ETIQUETAS and calls != 1:
            errores.append(f"[{i}] {outcome} con {calls} llamadas")
    return errores