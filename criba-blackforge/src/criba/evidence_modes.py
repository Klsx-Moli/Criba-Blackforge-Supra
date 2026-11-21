"""Explicit evidence modes for generated proposals.

``creative`` and ``exploratory`` are deliberately *not* validation states.
``validated`` is a request for the SUPRA gate, not a claim: a proposal stays
``VALIDACIÓN PENDIENTE`` until SUPRA reports ``verification PASS``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceMode:
    key: str
    label: str
    status: str
    caveat: str
    requires_supra_pass: bool = False


EVIDENCE_MODES: dict[str, EvidenceMode] = {
    "creative": EvidenceMode(
        key="creative",
        label="Creativo",
        status="NO VALIDADO",
        caveat="Propuesta creativa; novedad, viabilidad y eficacia no comprobadas.",
    ),
    "exploratory": EvidenceMode(
        key="exploratory",
        label="Exploratorio",
        status="NO VALIDADO",
        caveat="Hipótesis exploratoria; no es evidencia ni ha sido validada.",
    ),
    "validated": EvidenceMode(
        key="validated",
        label="Validado",
        status="VALIDACIÓN PENDIENTE",
        caveat=(
            "Modo validado: no se declara validado hasta que SUPRA emita "
            "verification PASS."
        ),
        requires_supra_pass=True,
    ),
}

DEFAULT_EVIDENCE_MODE = "creative"


def get_evidence_mode(key: str | None) -> EvidenceMode:
    """Return a declared mode; unknown identifiers are configuration errors."""
    normalized = str(key or DEFAULT_EVIDENCE_MODE)
    try:
        return EVIDENCE_MODES[normalized]
    except KeyError as exc:
        raise ValueError(f"modo de evidencia desconocido: {normalized}") from exc


def apply_evidence_mode(sheet: dict[str, Any], key: str) -> dict[str, Any]:
    """Attach the frozen evidence mode to a sheet and each generated entry.

    Returns a shallow copy with copied entries so the caller can persist the
    decision without mutating a sheet already held by another component.
    """
    spec = get_evidence_mode(key)
    out = dict(sheet)
    out["evidence_mode"] = spec.key
    out["evidence_mode_label"] = spec.label
    out["evidence_status"] = spec.status
    out["evidence_requires_supra_pass"] = spec.requires_supra_pass
    entries: list[dict[str, Any]] = []
    for entry in sheet.get("entries", []) or []:
        item = dict(entry)
        item["evidence_mode"] = spec.key
        item["evidence_mode_label"] = spec.label
        item["evidence_status"] = spec.status
        entries.append(item)
    out["entries"] = entries
    return out


def evidence_status(entry: dict[str, Any]) -> str:
    """Resolve status without promoting anything on the generation path."""
    spec = get_evidence_mode(entry.get("evidence_mode"))
    if not spec.requires_supra_pass:
        return spec.status
    verification = str(entry.get("verification_status") or "").strip().upper()
    return "VALIDADO" if verification == "PASS" else "VALIDACIÓN PENDIENTE"


def evidence_banner(entry: dict[str, Any]) -> str:
    """Human-readable mode banner for proposal views."""
    spec = get_evidence_mode(entry.get("evidence_mode"))
    status = evidence_status(entry)
    caveat = spec.caveat
    if status == "VALIDADO":
        caveat = (
            "SUPRA emitio verification PASS; la eficacia operativa sigue "
            "sujeta a prueba."
        )
    return f"MODO {spec.label.upper()} · {status}\n{caveat}"
