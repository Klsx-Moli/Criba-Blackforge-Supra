"""Registro transaccional: UNKNOWN = NULL, pendientes reintentables, historia íntegra."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from criba.storage import Storage

from .contrato import PROMPT_VERSION, SCHEMA_VERSION, validar_critica, validar_propuesta

_SCHEMA = """
CREATE TABLE IF NOT EXISTS interprete_decisions (
 combo_key TEXT NOT NULL, run_id TEXT NOT NULL, seed INTEGER, seed_key TEXT NOT NULL,
 activation_id TEXT NOT NULL, idea_id TEXT NOT NULL, modelo TEXT NOT NULL,
 labels_json TEXT NOT NULL, epistemic_score REAL, veredicto TEXT NOT NULL,
 evaluation_status TEXT NOT NULL, response_json TEXT NOT NULL,
 provenance_json TEXT NOT NULL, prompt_version TEXT NOT NULL, schema_version TEXT NOT NULL,
 raw_output_sha256 TEXT NOT NULL, fallback_used INTEGER NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY (combo_key, run_id, seed_key)
)
"""


class InterpreteStore:
    @staticmethod
    def cache_valido(
        row: dict[str, Any], idea: dict[str, Any], evidence: list[dict[str, Any]] | None = None
    ) -> bool:
        """Revalida datos históricos; una etiqueta CRITIQUED no acredita el contrato."""
        if (
            row.get("evaluation_status") != "CRITIQUED"
            or row.get("schema_version") != SCHEMA_VERSION
            or row.get("prompt_version") != PROMPT_VERSION
        ):
            return False
        try:
            response = row.get("response") or json.loads(row["response_json"])
            campos = response["interpretation"]["interprete_result"]
            critica = campos["critica"]
            return (
                isinstance(campos, dict)
                and campos.get("estado") == "PROPUESTA"
                and not validar_propuesta(campos, idea, evidence)
                and isinstance(critica, dict)
                and critica.get("evaluation_status") == "CRITIQUED"
                and isinstance(critica.get("respuesta"), dict)
                and not validar_critica(critica["respuesta"])
            )
        except (KeyError, TypeError, ValueError):
            return False

    def __init__(self, storage: Storage) -> None:
        self._storage = storage
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        con = self._storage.connect()
        try:
            with con:
                con.execute("BEGIN IMMEDIATE")
                columnas = {
                    r["name"] for r in con.execute("PRAGMA table_info(interprete_decisions)")
                }
                if columnas and "evaluation_status" not in columnas:
                    con.execute(
                        "ALTER TABLE interprete_decisions RENAME TO interprete_decisions_legacy_v1"
                    )
                    con.execute(_SCHEMA)
                    con.execute("""INSERT OR IGNORE INTO interprete_decisions
                        SELECT combo_key, run_id, seed,
                          CASE WHEN seed IS NULL THEN 'none' ELSE 'int:' || seed END,
                          activation_id, idea_id, modelo, labels_json, NULL, veredicto,
                          'LEGACY_UNVERIFIED', response_json, '{}', '', '', '', 0, created_at
                        FROM interprete_decisions_legacy_v1 ORDER BY rowid DESC""")
                    for row in con.execute(
                        "SELECT rowid, idea_id, modelo FROM interprete_decisions"
                    ).fetchall():
                        con.execute(
                            "UPDATE interprete_decisions SET combo_key=? WHERE rowid=?",
                            (self._combo_key(row["idea_id"], row["modelo"]), row["rowid"]),
                        )
                else:
                    con.execute(_SCHEMA)
                con.execute("""CREATE TABLE IF NOT EXISTS interprete_attempts (
                    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    combo_key TEXT NOT NULL, run_id TEXT NOT NULL, seed_key TEXT NOT NULL,
                    response_json TEXT NOT NULL, provenance_json TEXT NOT NULL,
                    evaluation_status TEXT NOT NULL, created_at TEXT NOT NULL)""")
        finally:
            con.close()

    @staticmethod
    def _combo_key(idea_id: str, modelo: str) -> str:
        return json.dumps([idea_id, modelo], ensure_ascii=False)

    @staticmethod
    def _seed_key(seed: int | None) -> str:
        if seed is not None and type(seed) is not int:
            raise ValueError("seed debe ser un entero o None")
        return "none" if seed is None else f"int:{seed}"

    def record_decision(
        self, activation_id: str, idea: dict[str, Any], modelo: str, run_id: str, seed: int | None
    ) -> dict[str, Any]:
        idea_id = idea["id"]
        combo = self._combo_key(idea_id, modelo)
        seed_key = self._seed_key(seed)
        now = datetime.now(UTC).isoformat()
        status = idea.get("interprete_evaluation_status", "NOT_EVALUATED")
        verdict = idea.get("interprete_verdict", "PENDIENTE_INTERPRETACION")
        interpretation = {k: v for k, v in idea.items() if k.startswith("interprete_")}
        response = json.dumps(
            {
                "input": {
                    k: v
                    for k, v in idea.items()
                    if not k.startswith("interprete_") and k != "_registro"
                },
                "interpretation": interpretation,
            },
            ensure_ascii=False,
        )
        provenance = idea.get("interprete_provenance") or {}
        prov_json = json.dumps(provenance, ensure_ascii=False)
        con = self._storage.connect()
        try:
            with con:
                con.execute("BEGIN IMMEDIATE")
                previo = con.execute(
                    "SELECT * FROM interprete_decisions WHERE "
                    "combo_key=? AND run_id=? AND seed_key=?",
                    (combo, run_id, seed_key),
                ).fetchone()
                if (
                    previo
                    and self.cache_valido(
                        dict(previo), idea, idea.get("interprete_evidence_delivered")
                    )
                    and (
                        previo["prompt_version"] == provenance.get("prompt_version", "")
                        and previo["schema_version"] == provenance.get("schema_version", "")
                        and json.loads(previo["provenance_json"]).get("prompt_sha256")
                        == provenance.get("prompt_sha256")
                        and json.loads(previo["provenance_json"]).get("generation_parameters", {})
                        == provenance.get("generation_parameters", {})
                    )
                ):
                    return {
                        "status": "deduplicated",
                        "score_previo": None,
                        "veredicto_previo": previo["veredicto"],
                    }
                con.execute(
                    "INSERT INTO interprete_attempts "
                    "(combo_key, run_id, seed_key, response_json, provenance_json, "
                    "evaluation_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (combo, run_id, seed_key, response, prov_json, status, now),
                )
                con.execute(
                    "DELETE FROM interprete_decisions WHERE "
                    "combo_key=? AND run_id=? AND seed_key=?",
                    (combo, run_id, seed_key),
                )
                con.execute(
                    "INSERT INTO interprete_decisions VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        combo,
                        run_id,
                        seed,
                        seed_key,
                        activation_id,
                        idea_id,
                        modelo,
                        json.dumps(idea.get("interprete_labels", [])),
                        None,
                        verdict,
                        status,
                        response,
                        prov_json,
                        provenance.get("prompt_version", ""),
                        provenance.get("schema_version", ""),
                        provenance.get("raw_output_sha256", ""),
                        int(bool(provenance.get("fallback_used", False))),
                        now,
                    ),
                )
            return {
                "status": "retried" if previo else "recorded",
                "combo_key": combo,
                "modelo": modelo,
                "veredicto": verdict,
                "score": None,
                "evaluation_status": status,
                "created_at": now,
            }
        finally:
            con.close()

    def get_verdict(
        self, idea_id: str, modelo: str, *, run_id: str | None = None, seed: int | None = None
    ) -> dict[str, Any] | None:
        """Exact run/seed when supplied; otherwise the most recent audit record."""
        con = self._storage.connect()
        try:
            sql = "SELECT * FROM interprete_decisions WHERE combo_key=?"
            params: list[Any] = [self._combo_key(idea_id, modelo)]
            if run_id is not None:
                sql += " AND run_id=? AND seed_key=?"
                params.extend([run_id, self._seed_key(seed)])
            row = con.execute(
                sql + " ORDER BY created_at DESC, rowid DESC LIMIT 1", params
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            for column, name, expected, empty in (
                ("labels_json", "labels", list, []),
                ("response_json", "response", dict, {}),
                ("provenance_json", "provenance", dict, {}),
            ):
                raw = result.pop(column)
                try:
                    parsed = json.loads(raw)
                    if not isinstance(parsed, expected):
                        raise ValueError("tipo almacenado incompatible")
                    result[name] = parsed
                except (ValueError, TypeError):
                    result[name] = empty
                    result[column] = raw  # conserva el dato dañado para auditoría
                    result["evaluation_status"] = "CACHE_INVALID"
                    result["cache_error"] = column + ":INVALID_JSON_OR_TYPE"
            return result
        finally:
            con.close()
