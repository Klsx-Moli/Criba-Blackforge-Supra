from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_DB,
    VALID_DECISIONS,
)

SCHEMA_VERSION = 1


def _encode_combo_key(left: object, right: object) -> str:
    """Encode an unordered method pair without breaking legacy safe keys."""
    first, second = sorted((str(left), str(right)))
    if "::" not in first and "::" not in second:
        return f"{first}::{second}"
    return json.dumps([first, second], ensure_ascii=False, separators=(",", ":"))


def _decode_combo_key(raw_value: object) -> tuple[str, str] | None:
    """Decode canonical JSON keys and unambiguous legacy delimiter keys."""
    raw = str(raw_value)
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        parsed = None
    if (
        isinstance(parsed, list)
        and len(parsed) == 2
        and all(isinstance(item, str) for item in parsed)
    ):
        return parsed[0], parsed[1]
    parts = raw.split("::")
    if len(parts) == 2:
        return parts[0], parts[1]
    return None


class Storage:
    def __init__(self, path: Path | str | None = DEFAULT_DB) -> None:
        self.path = Path(path or DEFAULT_DB)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        # timeout mas alto: initialize() ejecuta DDL idempotente en cada
        # conexion y, bajo escritores concurrentes, 3s no bastaba (el test
        # de concurrencia de BLACKFORGE fallaba con "database is locked").
        con = sqlite3.connect(self.path, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA journal_mode = WAL")
        # busy_timeout explicito: hace que un escritor espere en C en lugar
        # de fallar en Python, tambien para las conexiones que llegan
        # mientras otra sostiene el lock de escritura.
        con.execute("PRAGMA busy_timeout = 30000")
        return con

    def initialize(self) -> None:
        con = self.connect()
        try:
            current_version = int(con.execute("PRAGMA user_version").fetchone()[0])
            if current_version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"La base usa una versión de esquema más nueva ({current_version}) "
                    f"que la soportada ({SCHEMA_VERSION})."
                )
            with con:
                con.execute('''CREATE TABLE IF NOT EXISTS sessions (
                  id TEXT PRIMARY KEY, created_at TEXT NOT NULL, query_hash TEXT NOT NULL,
                  query TEXT NOT NULL, current_id TEXT NOT NULL, status TEXT NOT NULL,
                  config_json TEXT NOT NULL, packet_json TEXT NOT NULL, evidence_json TEXT NOT NULL DEFAULT '[]')''')
                con.execute('''CREATE TABLE IF NOT EXISTS decisions (
                  id TEXT PRIMARY KEY, session_id TEXT NOT NULL, created_at TEXT NOT NULL,
                  status TEXT NOT NULL, evidence_json TEXT NOT NULL, note TEXT NOT NULL,
                  FOREIGN KEY(session_id) REFERENCES sessions(id))''')
                con.execute('''CREATE TABLE IF NOT EXISTS chain_sessions (
                  chain_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, original_objective TEXT NOT NULL,
                  current_stage INTEGER NOT NULL, status TEXT NOT NULL)''')
                con.execute('''CREATE TABLE IF NOT EXISTS chain_memory (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, chain_id TEXT NOT NULL, stage INTEGER NOT NULL,
                  field_name TEXT NOT NULL, field_value TEXT NOT NULL,
                  FOREIGN KEY(chain_id) REFERENCES chain_sessions(chain_id))''')
                con.execute('''CREATE TABLE IF NOT EXISTS chain_outputs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, chain_id TEXT NOT NULL, stage INTEGER NOT NULL,
                  output_json TEXT NOT NULL,
                  FOREIGN KEY(chain_id) REFERENCES chain_sessions(chain_id))''')
                con.execute('''CREATE TABLE IF NOT EXISTS chain_reviews (
                  review_id TEXT PRIMARY KEY, chain_id TEXT NOT NULL, stage INTEGER NOT NULL,
                  decision TEXT NOT NULL, review_json TEXT NOT NULL,
                  FOREIGN KEY(chain_id) REFERENCES chain_sessions(chain_id))''')
                con.execute('''CREATE TABLE IF NOT EXISTS lottery_used_combinations (
                  catalog_fingerprint TEXT NOT NULL,
                  combo_key TEXT NOT NULL,
                  first_seen_at TEXT NOT NULL,
                  run_id TEXT NOT NULL,
                  mode TEXT NOT NULL,
                  seed INTEGER,
                  PRIMARY KEY (catalog_fingerprint, combo_key))''')
                con.execute('''CREATE TABLE IF NOT EXISTS semantic_reservations (
                  scope TEXT NOT NULL,
                  attempt TEXT NOT NULL,
                  request_sha256 TEXT NOT NULL,
                  reviewer TEXT NOT NULL,
                  status TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  closed_at TEXT,
                  receipt_sha256 TEXT,
                  PRIMARY KEY (scope, attempt))''')
                con.execute('''CREATE TABLE IF NOT EXISTS semantic_receipts (
                  scope TEXT NOT NULL,
                  attempt TEXT NOT NULL,
                  request_sha256 TEXT NOT NULL,
                  body_sha256 TEXT NOT NULL,
                  status TEXT NOT NULL,
                  received_at TEXT NOT NULL,
                  PRIMARY KEY (scope, attempt, body_sha256))''')
                if current_version < SCHEMA_VERSION:
                    con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        finally:
            con.close()

    def save(self, query: str, packet: Mapping[str, Any], config: Mapping[str, Any]) -> str:
        ident = str(packet["activation_id"])
        now = str(packet["timestamp"])
        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
        con = self.connect()
        try:
            with con:
                con.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)", (ident, now, digest, query, packet["selected_current"]["id"], "ACTIVATED", json.dumps(config, ensure_ascii=False), json.dumps(packet, ensure_ascii=False), "[]"))
            return ident
        finally:
            con.close()

    def save_invention(
        self, sheet: Mapping[str, Any], selected_index: int = 0,
    ) -> str:
        """Preserve an interpreted run in the existing history, without evaluation.

        Each save has its own identity: a seed/run ID may be reused with a
        different model response. The complete sheet remains recoverable.
        """
        query = sheet.get("query")
        entries = sheet.get("entries")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("La propuesta requiere un problema no vacío.")
        if (
            not isinstance(entries, list)
            or type(selected_index) is not int
            or not 0 <= selected_index < len(entries)
        ):
            raise ValueError("Selecciona una propuesta de la sesión.")
        selected = entries[selected_index]
        if (
            not isinstance(selected, dict)
            or selected.get("estado_interpretacion") != "PROPUESTA"
            or not isinstance(selected.get("mecanismo"), str)
            or not selected["mecanismo"].strip()
        ):
            raise ValueError("No hay una propuesta interpretada que guardar.")
        packet = {
            "kind": "invention_sheet",
            "sheet": dict(sheet),
            "selected_index": selected_index,
        }
        encoded = json.dumps(packet, ensure_ascii=False, allow_nan=False)
        ident = "invention-" + uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
        current_id = str(selected.get("candidate_id") or selected.get("id") or selected_index)
        con = self.connect()
        try:
            with con:
                con.execute(
                    "INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
                    (ident, now, digest, query, current_id, "PROPUESTA",
                     '{"kind":"invention_sheet","schema_version":1}', encoded, "[]"),
                )
            return ident
        finally:
            con.close()

    def save_blackforge_session(
        self,
        session_id: str,
        query: str,
        packet: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> str:
        """Persist a BLACKFORGE packet under its logical session identity."""
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id de BLACKFORGE debe ser no vacío.")
        timestamp = packet.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError("El packet BLACKFORGE requiere timestamp.")
        status = packet.get("status")
        if not isinstance(status, str) or not status.strip():
            raise ValueError("El packet BLACKFORGE requiere status.")
        packet_session_id = packet.get("session_id")
        if packet_session_id != session_id:
            raise ValueError("session_id no coincide con el packet BLACKFORGE.")
        packet_query = packet.get("query")
        if packet_query != query:
            raise ValueError("query no coincide con el packet BLACKFORGE.")

        selection = packet.get("selection")
        selected_ids: object = []
        if isinstance(selection, Mapping):
            selected_ids = selection.get("selected_ids", [])
        current_id = ""
        if isinstance(selected_ids, list):
            current_id = next(
                (
                    item
                    for item in selected_ids
                    if isinstance(item, str) and item.strip()
                ),
                "",
            )

        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
        con = self.connect()
        try:
            with con:
                con.execute(
                    "INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        session_id,
                        timestamp,
                        digest,
                        query,
                        current_id,
                        status,
                        json.dumps(dict(config), ensure_ascii=False),
                        json.dumps(dict(packet), ensure_ascii=False),
                        "[]",
                    ),
                )
            return session_id
        finally:
            con.close()

    def record_event(
        self,
        session_id: str,
        event_type: str,
        evidence: list[Any] | dict[str, Any],
        note: str = "",
    ) -> dict[str, Any]:
        """Append a BLACKFORGE audit event without touching CRIBA decisions."""
        valid_events = {"mitigation_proposed", "mitigation_applied"}
        if event_type not in valid_events:
            raise ValueError("Tipo de evento BLACKFORGE inválido.")
        if not isinstance(evidence, (list, dict)):
            raise ValueError("evidence debe ser una lista o un objeto.")

        entry: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": event_type,
            "evidence": evidence,
            "note": note,
        }
        con = self.connect()
        try:
            # BEGIN IMMEDIATE: toma el lock de escritura ANTES del SELECT.
            # Con BEGIN diferido, dos hilos podian leer el mismo evidence_json
            # y luego competir por el UPDATE: uno recibia "database is locked".
            # Es el mismo defecto que corregi en las reservas semanticas.
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT evidence_json FROM sessions WHERE id=?",
                (session_id,),
            ).fetchone()
            if not row:
                raise ValueError(f"Sesión inexistente: {session_id}")
            existing = json.loads(row["evidence_json"])
            if not isinstance(existing, list):
                raise ValueError("evidence_json almacenado debe ser una lista.")
            updated = [*existing, entry]
            con.execute(
                "UPDATE sessions SET evidence_json=? WHERE id=?",
                (json.dumps(updated, ensure_ascii=False), session_id),
            )
            con.commit()
            return entry
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def get(self, ident: str) -> dict[str, Any]:
        con = self.connect()
        try:
            row = con.execute("SELECT * FROM sessions WHERE id=?", (ident,)).fetchone()
            if not row:
                raise ValueError(f"Sesión inexistente: {ident}")
            result: dict[str, Any] = {str(key): row[key] for key in row.keys()}
            for key in ("config_json", "packet_json", "evidence_json"):
                result[key[:-5]] = json.loads(result.pop(key))
            return result
        finally:
            con.close()

    def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        con = self.connect()
        try:
            rows = con.execute("SELECT id,created_at,query,current_id,status FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [{str(key): row[key] for key in row.keys()} for row in rows]
        finally:
            con.close()

    def record_decision(self, session_id: str, status: str, evidence: list[Any] | dict[str, Any], note: str = "") -> dict[str, Any]:
        if status not in VALID_DECISIONS:
            raise ValueError("Estado de decisión inválido.")
        if not isinstance(evidence, (list, dict)):
            raise ValueError("evidence debe ser una lista o un objeto.")

        entry: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "evidence": evidence,
            "note": note,
        }
        con = self.connect()
        try:
            with con:
                # BEGIN IMMEDIATE: toma el lock de ESCRITURA antes del SELECT.
                # Sin esto, dos escritores podian leer el mismo evidence_json y
                # uno sobrescribia al otro (perdida silenciosa de evidencia).
                # Es la misma reparacion aplicada en record_event.
                con.execute("BEGIN IMMEDIATE")
                row = con.execute(
                    "SELECT evidence_json FROM sessions WHERE id=?", (session_id,)
                ).fetchone()
                if not row:
                    raise ValueError(f"Sesión inexistente: {session_id}")
                existing = json.loads(row["evidence_json"])
                if not isinstance(existing, list):
                    raise ValueError("evidence_json almacenado debe ser una lista.")
                updated = [*existing, entry]
                con.execute(
                    "INSERT INTO decisions VALUES(?,?,?,?,?,?)",
                    (
                        entry["id"],
                        session_id,
                        entry["timestamp"],
                        status,
                        json.dumps(evidence, ensure_ascii=False),
                        note,
                    ),
                )
                con.execute(
                    "UPDATE sessions SET status=?, evidence_json=? WHERE id=?",
                    (status, json.dumps(updated, ensure_ascii=False), session_id),
                )
            return entry
        finally:
            con.close()

    def compare(self, a: str, b: str) -> dict[str, Any]:
        left, right = self.get(a), self.get(b)
        lp, rp = left["packet"], right["packet"]
        return {"session_a": a, "session_b": b, "same_query_hash": left["query_hash"] == right["query_hash"], "currents": {"a": lp["selected_current"]["id"], "b": rp["selected_current"]["id"]}, "methods": {"a": [x["id"] for x in lp["supporting_methods"]], "b": [x["id"] for x in rp["supporting_methods"]]}, "decisions": {"a": lp["decision"], "b": rp["decision"]}}

    def save_chain_session(self, chain_id: str, original_objective: str, current_stage: int, status: str) -> None:
        now = str(datetime.now(timezone.utc).isoformat())
        con = self.connect()
        try:
            with con:
                con.execute(
                    "INSERT OR REPLACE INTO chain_sessions VALUES(?,?,?,?,?)",
                    (chain_id, now, original_objective, current_stage, status),
                )
        finally:
            con.close()

    def save_chain_memory(self, chain_id: str, stage: int, memory: Mapping[str, Any]) -> None:
        con = self.connect()
        try:
            with con:
                # BEGIN IMMEDIATE: el SELECT de "ya guardado" y el INSERT
                # deben ser una sola operacion atomica. Sin el lock, dos
                # hilos podian no ver la fila del otro y guardar el mismo
                # campo dos veces (duplicado de identidad), o pisarse el
                # valor en el caso de campos con valores distintos.
                con.execute("BEGIN IMMEDIATE")
                for field_name, value in memory.items():
                    if isinstance(value, (list, dict)):
                        field_value = json.dumps(value, ensure_ascii=False)
                    else:
                        field_value = str(value)
                    already_saved = con.execute(
                        "SELECT 1 FROM chain_memory WHERE chain_id=? AND stage=? "
                        "AND field_name=? AND field_value=? LIMIT 1",
                        (chain_id, stage, field_name, field_value),
                    ).fetchone()
                    if already_saved:
                        continue
                    con.execute(
                        "INSERT INTO chain_memory(chain_id, stage, field_name, field_value) VALUES(?,?,?,?)",
                        (chain_id, stage, field_name, field_value),
                    )
        finally:
            con.close()

    def save_chain_output(self, chain_id: str, stage: int, output: Mapping[str, Any]) -> None:
        """Persist a typed stage output for cold reconstruction."""
        con = self.connect()
        try:
            with con:
                con.execute(
                    "INSERT INTO chain_outputs(chain_id, stage, output_json) VALUES(?,?,?)",
                    (chain_id, stage, json.dumps(dict(output), ensure_ascii=False)),
                )
        finally:
            con.close()

    def load_chain_outputs(self, chain_id: str) -> list[dict[str, Any]]:
        """Load stage outputs in execution order."""
        con = self.connect()
        try:
            rows = con.execute(
                "SELECT id, chain_id, stage, output_json FROM chain_outputs "
                "WHERE chain_id=? ORDER BY stage, id",
                (chain_id,),
            ).fetchall()
            return [
                {"id": row["id"], "chain_id": row["chain_id"], "stage": row["stage"],
                 "output": json.loads(row["output_json"])}
                for row in rows
            ]
        finally:
            con.close()

    def save_chain_review(self, review_id: str, chain_id: str, stage: int,
                          decision: str, review: Mapping[str, Any]) -> None:
        """Persist one human decision record idempotently by review_id."""
        con = self.connect()
        try:
            with con:
                con.execute(
                    "INSERT OR IGNORE INTO chain_reviews "
                    "(review_id, chain_id, stage, decision, review_json) VALUES(?,?,?,?,?)",
                    (review_id, chain_id, stage, decision,
                     json.dumps(dict(review), ensure_ascii=False)),
                )
        finally:
            con.close()

    def load_chain_reviews(self, chain_id: str) -> list[dict[str, Any]]:
        """Load persisted human decisions in stage order."""
        con = self.connect()
        try:
            rows = con.execute(
                "SELECT review_id, chain_id, stage, decision, review_json FROM chain_reviews "
                "WHERE chain_id=? ORDER BY stage, review_id",
                (chain_id,),
            ).fetchall()
            return [
                {"review_id": row["review_id"], "chain_id": row["chain_id"],
                 "stage": row["stage"], "decision": row["decision"],
                 "review": json.loads(row["review_json"])}
                for row in rows
            ]
        finally:
            con.close()

    def load_chain_session(self, chain_id: str) -> dict[str, Any]:
        con = self.connect()
        try:
            row = con.execute("SELECT * FROM chain_sessions WHERE chain_id=?", (chain_id,)).fetchone()
            if not row:
                raise ValueError(f"Chain inexistente: {chain_id}")
            return {k: row[k] for k in row.keys()}
        finally:
            con.close()

    def load_chain_memory(self, chain_id: str) -> list[dict[str, Any]]:
        con = self.connect()
        try:
            rows = con.execute(
                "SELECT id, chain_id, stage, field_name, field_value FROM chain_memory WHERE chain_id=? ORDER BY stage, id",
                (chain_id,),
            ).fetchall()
            return [{k: row[k] for k in row.keys()} for row in rows]
        finally:
            con.close()

    def save_lottery_combinations(
        self,
        catalog_fingerprint: str,
        combinations_list: Sequence[tuple[str, str]],
        run_id: str = "lottery-run",
        mode: str = "alternating",
        seed: int | None = None,
    ) -> int:
        """Persist used method pairs to SQLite for cross-session deduplication."""
        now = datetime.now(timezone.utc).isoformat()
        saved = 0
        con = self.connect()
        try:
            with con:
                for left, right in combinations_list:
                    combo_key = _encode_combo_key(left, right)
                    try:
                        cursor = con.execute(
                            "INSERT OR IGNORE INTO lottery_used_combinations VALUES(?,?,?,?,?,?)",
                            (catalog_fingerprint, combo_key, now, run_id, mode, seed),
                        )
                        saved += max(cursor.rowcount, 0)
                    except sqlite3.IntegrityError:
                        pass
            return saved
        finally:
            con.close()

    def load_used_lottery_combinations(self, catalog_fingerprint: str) -> set[tuple[str, str]]:
        """Load all historically used method pairs for this catalog fingerprint."""
        con = self.connect()
        try:
            rows = con.execute(
                "SELECT combo_key FROM lottery_used_combinations WHERE catalog_fingerprint=?",
                (catalog_fingerprint,),
            ).fetchall()
            combos: set[tuple[str, str]] = set()
            for r in rows:
                pair = _decode_combo_key(r[0])
                if pair is not None:
                    combos.add(pair)
            return combos
        finally:
            con.close()

    def load_combination_first_seen(self, catalog_fingerprint: str) -> dict[tuple[str, str], str]:
        """Primer uso registrado por combinación (fatiga por decaimiento).

        La PK (fingerprint, combo_key) impide contar usos sin migración; el
        cooldown honesto usa first_seen_at: uso reciente = penalización
        fuerte, uso antiguo = débil, nunca prohibición permanente.
        """
        con = self.connect()
        try:
            rows = con.execute(
                "SELECT combo_key, first_seen_at FROM lottery_used_combinations "
                "WHERE catalog_fingerprint=?",
                (catalog_fingerprint,),
            ).fetchall()
            out: dict[tuple[str, str], str] = {}
            for r in rows:
                pair = _decode_combo_key(r[0])
                if pair is not None:
                    out[pair] = str(r[1])
            return out
        finally:
            con.close()

    # ------------------------------------------------------------------
    # Reserva de intento y cierre condicional (K3)
    # ------------------------------------------------------------------
    def reserve_semantic_attempt(
        self,
        scope: str,
        attempt: str,
        request_sha256: str,
        reviewer: str,
    ) -> bool:
        """Reserva (o RE-RESERVA) el intento activo de un scope.

        Devuelve True si esta llamada crea la reserva vigente y False si
        repite exactamente la misma peticion ya reservada.

        Semantica de reintento: un scope tiene UN intento activo. Si llega
        una peticion nueva (otro ``request_sha256``) para el mismo intento,
        SUSTITUYE a la anterior y la anterior pasa a ``SUPERSEDED``. Esto es
        lo que hace que una respuesta tardia del intento 1 ya no pueda cerrar
        la reserva que ahora pertenece al intento 2.
        """
        if not scope or not attempt:
            raise ValueError("scope y attempt son obligatorios")
        now = datetime.now(timezone.utc).isoformat()
        con = self.connect()
        try:
            # BEGIN IMMEDIATE toma el lock de ESCRITURA antes de leer. Sin
            # esto, dos conexiones podian leer ACTIVE a la vez y ambas
            # creerse ganadoras: la carrera real lo demostro.
            con.execute("BEGIN IMMEDIATE")
            fila = con.execute(
                "SELECT request_sha256 FROM semantic_reservations "
                "WHERE scope=? AND attempt=?",
                (scope, attempt),
            ).fetchone()
            if fila is not None and str(fila[0]) == request_sha256:
                con.commit()
                # Misma peticion repetida: idempotente, no es reserva nueva.
                return False
            if fila is not None:
                # Reintento legitimo del mismo attempt: la reserva anterior
                # queda superada. Con PK (scope, attempt) no pueden coexistir
                # dos filas, asi que se reemplaza la vigente.
                con.execute(
                    "DELETE FROM semantic_reservations "
                    "WHERE scope=? AND attempt=?",
                    (scope, attempt),
                )
            con.execute(
                "INSERT INTO semantic_reservations "
                "(scope, attempt, request_sha256, reviewer, status, created_at) "
                "VALUES(?,?,?,?,?,?)",
                (scope, attempt, request_sha256, reviewer, "ACTIVE", now),
            )
            con.commit()
            return True
        finally:
            con.close()

    def close_semantic_attempt(
        self,
        scope: str,
        attempt: str,
        request_sha256: str,
        receipt_sha256: str,
    ) -> str:
        """Cierra SOLO si el recibo corresponde a la reserva VIGENTE.

        Devuelve uno de:
          - ``CLOSED``: el recibo corresponde a la peticion activa y se cierra.
          - ``ALREADY_CLOSED``: ya estaba cerrado con este mismo recibo.
          - ``STALE``: la peticion ya fue superada por un reintento; el
            recibo se conserva para auditoria pero NO queda vigente.
          - ``UNKNOWN``: no existe reserva para ese scope/attempt.

        ``STALE`` es el caso critico de K3: la respuesta tardia del intento 1
        llega despues de que el intento 2 re-reservo el mismo scope, asi que
        no cierra nada vigente.
        """
        now = datetime.now(timezone.utc).isoformat()
        con = self.connect()
        try:
            # BEGIN IMMEDIATE: el lock de escritura se toma ANTES de leer el
            # estado. Sin esto, dos cierres concurrentes leian ACTIVE y
            # ambos devolvia CLOSED. La carrera real lo detecto.
            con.execute("BEGIN IMMEDIATE")
            fila = con.execute(
                "SELECT request_sha256, status, receipt_sha256 "
                "FROM semantic_reservations WHERE scope=? AND attempt=?",
                (scope, attempt),
            ).fetchone()
            if fila is None:
                con.rollback()
                return "UNKNOWN"
            request_actual, status_actual, receipt_actual = (
                str(fila[0]), str(fila[1]), fila[2]
            )
            es_vigente = request_actual == request_sha256
            # El recibo se persiste siempre, incluso si llega tarde.
            con.execute(
                "INSERT OR IGNORE INTO semantic_receipts "
                "(scope, attempt, request_sha256, body_sha256, status, "
                "received_at) VALUES(?,?,?,?,?,?)",
                (
                    scope,
                    attempt,
                    request_sha256,
                    receipt_sha256,
                    status_actual if es_vigente else "STALE",
                    now,
                ),
            )
            if not es_vigente:
                con.commit()
                return "STALE"
            if status_actual != "ACTIVE":
                if receipt_actual is not None and str(receipt_actual) == receipt_sha256:
                    con.commit()
                    return "ALREADY_CLOSED"
                # Mismo intento, cuerpo distinto: conflicto, no reemplazo.
                con.rollback()
                raise ValueError(
                    "conflicto: el intento ya esta cerrado con otro recibo"
                )
            cursor = con.execute(
                "UPDATE semantic_reservations SET status=?, closed_at=?, "
                "receipt_sha256=? WHERE scope=? AND attempt=? "
                "AND request_sha256=? AND status=?",
                ("CLOSED", now, receipt_sha256, scope, attempt,
                 request_sha256, "ACTIVE"),
            )
            # El UPDATE condicional es la garantia final: si otra conexion
            # cerro entre la lectura y la escritura, rowcount es 0.
            if cursor.rowcount != 1:
                con.rollback()
                return "ALREADY_CLOSED"
            con.commit()
            return "CLOSED"
        finally:
            con.close()

    def semantic_attempt_status(self, scope: str, attempt: str) -> dict[str, Any] | None:
        """Estado legible de una reserva, o None si no existe."""
        con = self.connect()
        try:
            fila = con.execute(
                "SELECT attempt, request_sha256, reviewer, status, created_at, "
                "closed_at, receipt_sha256 FROM semantic_reservations "
                "WHERE scope=? AND attempt=?",
                (scope, attempt),
            ).fetchone()
            if fila is None:
                return None
            return {
                "attempt": fila[0],
                "request_sha256": fila[1],
                "reviewer": fila[2],
                "status": fila[3],
                "created_at": fila[4],
                "closed_at": fila[5],
                "receipt_sha256": fila[6],
            }
        finally:
            con.close()

    def load_semantic_receipts(
        self, scope: str, attempt: str
    ) -> list[dict[str, Any]]:
        """Recibos persistidos de un intento, incluidos los tardios.

        Un recibo STALE sigue aqui para auditoria, pero su ``status`` deja
        claro que no cierra la reserva vigente.
        """
        con = self.connect()
        try:
            rows = con.execute(
                "SELECT request_sha256, body_sha256, status, received_at "
                "FROM semantic_receipts WHERE scope=? AND attempt=? "
                "ORDER BY received_at",
                (scope, attempt),
            ).fetchall()
            return [
                {
                    "request_sha256": r[0],
                    "body_sha256": r[1],
                    "status": r[2],
                    "received_at": r[3],
                }
                for r in rows
            ]
        finally:
            con.close()
