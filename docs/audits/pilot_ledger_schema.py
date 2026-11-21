#!/usr/bin/env python3
"""Ledger experimental del piloto del selector (ESQUEMA, NO APROBADO).

Uso EXCLUSIVAMENTE de preparación técnica. No es evidencia experimental.
Fuente de verdad de los requisitos: PROMPT_10_PILOTO_SELECTOR_CRIBA.md §4.

DECISIÓN DEL PROPIETARIO (2026-10-22): se acepta como estructura de trabajo la
descomposición 9 apartados canónicos -> 27 campos atómicos -> 15 bloques
temáticos, **sometida a cotejo de cobertura**. Se retira la exigencia de
exactamente 15 campos atómicos.

    LEDGER_DESIGN_DECISION = ACCEPTED_WITH_COVERAGE_CHECK
    LEDGER_SCHEMA_STATUS  = PENDING_NOT_APPROVED
    PREREGISTRATION_STATUS = NOT_APPROVED
    PILOT_EXECUTION_ALLOWED = NO

Este módulo es append-only por diseño: cada fila enlaza con el hash de la
anterior. Ver docs/audits/PROMPT_10_LEDGER_ESQUEMA.md.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_ID = "pilot-selector-ledger/1"
GENESIS = "GENESIS"
# Marca inequívoca: ninguna fila de este módulo es evidencia experimental.
SYNTHETIC_MARK = "SYNTHETIC / NOT_EXPERIMENTAL_EVIDENCE"

# 15 bloques temáticos -> 27 campos atómicos (derivados de los 9 apartados).
BLOCKS: dict[str, tuple[str, ...]] = {
    "B1_episode_identity": ("episode_id", "root_problem_id", "candidate_set_hash", "split"),
    "B2_context_conditions": ("context_before", "available_conditions", "versions"),
    "B3_prediction": ("prediction_before",),
    "B4_selector_decision": ("selector_rule", "ranking", "selected_decision", "ties"),
    "B5_propensity": ("propensity",),
    "B6_executed_artifact": ("executed_artifact",),
    "B7_claim_protocol": ("mechanistic_claim", "rival_claim", "protocol_hash"),
    "B8_controls_observables": ("controls", "observables_units", "decision_rule"),
    "B9_execution": ("execution", "deviations", "failures"),
    "B10_observation": ("observation",),
    "B11_functional_result": ("functional_result",),
    "B12_interpretation": ("interpretation", "posterior_decision"),
    "B13_integrity": ("integrity_status",),
    "B14_evidence_link": ("evidence_link",),
    "B15_arm_accounting": ("arm", "seed", "budget", "raw_result", "verdict", "provenance"),
}

ATOMIC_FIELDS = tuple(f for fields in BLOCKS.values() for f in fields)
REQUIRED_BLOCKS = tuple(BLOCKS)


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_synthetic_row(episode_id: str = "EP-SYNTHETIC-000") -> dict[str, Any]:
    """Construye una fila íntegramente sintética para validar el esquema.

    Ningún campo proviene de una ejecución real. Sirve solo para comprobar que
    los 27 campos atómicos / 15 bloques tienen forma y que la cadena append-only
    los enlaza.
    """
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema": SCHEMA_ID,
        "synthetic": SYNTHETIC_MARK,
        "episode_id": episode_id,
        "root_problem_id": "SYNTHETIC-PROBLEM",
        "candidate_set_hash": "sha256:" + _hash_bytes(b"synthetic-candidate-set"),
        "split": "exploratory",
        "context_before": {"note": "synthetic placeholder"},
        "available_conditions": {"note": "synthetic placeholder"},
        "versions": {"modelo": "UNKNOWN", "herramientas": "UNKNOWN", "corpus": "UNKNOWN"},
        "prediction_before": {"prediccion": "UNKNOWN", "origen": "SYNTHETIC", "disponible_en": now},
        "selector_rule": "SYNTHETIC (no executed)",
        "ranking": [],
        "selected_decision": {"candidate": None, "note": "SYNTHETIC"},
        "ties": [],
        "propensity": "UNKNOWN",
        "executed_artifact": {"hash": None, "version": None, "diff_vs_selected": None},
        "mechanistic_claim": "NONE (synthetic)",
        "rival_claim": "NONE (synthetic)",
        "protocol_hash": "sha256:" + _hash_bytes(b"not-a-protocol"),
        "controls": {"positivo": "NOT_RUN", "negativo": "NOT_RUN", "invalido": "NOT_RUN"},
        "observables_units": {"observable": "NONE", "unidades": "NONE"},
        "decision_rule": "NONE (synthetic)",
        "execution": {"ambiente": "SYNTHETIC", "tiempos": None, "comandos": [], "trace": []},
        "deviations": [],
        "failures": {"retries": 0, "timeouts": 0, "costes": "UNKNOWN"},
        "observation": {"valor": None, "instrumento": "NONE", "fuente": "SYNTHETIC",
                        "timestamp": now, "ausencia": "SYNTHETIC_ROW"},
        "functional_result": "UNKNOWN",
        "interpretation": "SYNTHETIC row: not experimental evidence",
        "posterior_decision": "NONE",
        "integrity_status": "OK",
        "evidence_link": "SYNTHETIC",
        "arm": "SYNTHETIC",
        "seed": "UNKNOWN",
        "budget": "UNKNOWN",
        "raw_result": {},
        "verdict": "INVALID_EXECUTION",
        "provenance": "DECLARED",
    }


class PilotLedger:
    """Ledger append-only por episodio (preparación; no aprobado)."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _prev_hash(self) -> str:
        if not self.path.exists():
            return GENESIS
        return _hash_bytes(self.path.read_bytes())

    def append(self, row: dict[str, Any]) -> str:
        payload = {**row, "prev_hash": self._prev_hash()}
        line = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as fh:
            fh.write(line)
        return _hash_bytes(line)

    def verify_chain(self) -> tuple[bool, str]:
        """Verifica la cadena append-only. Devuelve (ok, detalle)."""
        if not self.path.exists():
            return True, "empty ledger"
        lines = self.path.read_bytes().splitlines(keepends=True)
        prev = GENESIS
        for idx, line in enumerate(lines, start=1):
            row = json.loads(line)
            if row.get("prev_hash") != prev:
                return False, f"fila {idx}: prev_hash no enlaza"
            prev = _hash_bytes(line)
        return True, f"{len(lines)} filas enlazadas"

    def coverage(self, row: dict[str, Any]) -> dict[str, Any]:
        """Coteja cobertura: 15 bloques y 27 campos atómicos."""
        missing = [f for f in ATOMIC_FIELDS if f not in row]
        present_blocks = [b for b in REQUIRED_BLOCKS if all(f in row for f in BLOCKS[b])]
        return {
            "blocks_total": len(REQUIRED_BLOCKS),
            "blocks_present": len(present_blocks),
            "blocks_missing": [b for b in REQUIRED_BLOCKS if b not in present_blocks],
            "atomic_total": len(ATOMIC_FIELDS),
            "atomic_missing": missing,
            "covered": not missing and len(present_blocks) == len(REQUIRED_BLOCKS),
        }


if __name__ == "__main__":
    import tempfile

    tmp = Path(tempfile.mkdtemp()) / "pilot_ledger.jsonl"
    ledger = PilotLedger(tmp)
    row = build_synthetic_row()
    ledger.append(row)
    ledger.append(build_synthetic_row("EP-SYNTHETIC-001"))
    ok, detail = ledger.verify_chain()
    cov = ledger.coverage(row)
    print(f"LEDGER_SCHEMA_STATUS = PENDING_NOT_APPROVED")
    print(f"LEDGER_DESIGN_DECISION = ACCEPTED_WITH_COVERAGE_CHECK")
    print(f"synthetic_row = {SYNTHETIC_MARK}")
    print(f"cadena append-only: {ok} ({detail})")
    print(f"cobertura: bloques {cov['blocks_present']}/{cov['blocks_total']}, "
          f"campos atomicos {cov['atomic_total'] - len(cov['atomic_missing'])}/{cov['atomic_total']}")
    print(f"cubierto: {cov['covered']}")
