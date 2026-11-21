"""Validador aislado de fichas, operadores y fuentes de la campaña TRIZ+Koestler.

ALCANCE: laboratorio. No es un contrato productivo ni modifica runtime.
Valida invariantes epistemológicas del bundle (ausente != null != vacio != cero != UNKNOWN)
y la integridad referencial de las colas documentales generadas por IMP-01/IMP-02.

EVIDENCIA: STATICALLY_INSPECTED para la logica; VERIFIED_BY_EXECUTION solo cuando
se ejecutan las pruebas dirigidas (test_validador.py).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Palabras/valores que NO se equiparan. Regla del bundle.
UNKNOWN_TOKENS = {"UNKNOWN", "UNKNOWN:", "null", "None", ""}
ZERO_TOKENS = {"0", "0.0", 0, 0.0}


class ValidationError:
    __slots__ = ("code", "locator", "message")

    def __init__(self, code: str, locator: str, message: str) -> None:
        self.code = code
        self.locator = locator
        self.message = message

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "locator": self.locator, "message": self.message}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(str(path))
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            out.append(json.loads(raw))
    return out


def _is_unknown(value: Any) -> bool:
    # Marcadores delimitados reconocidos por el contrato: None, cadena vacía,
    # "UNKNOWN" exacto y "UNKNOWN: <explicación>". No startswith indiscriminado:
    # "UNKNOWNLAND" no es un marcador. Esta clasificación NO se extrapola a otros
    # campos: ausente / null / vacío / cero / UNKNOWN conservan sus distinciones.
    if value is None:
        return True
    if isinstance(value, str):
        s = value.strip().upper()
        if s == "" or s == "UNKNOWN" or s.startswith("UNKNOWN:"):
            return True
    return False


def _is_zero(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)) and value == 0:
        return True
    if isinstance(value, str) and value.strip() in {"0", "0.0"}:
        return True
    return False


def validate_sources(sources: list[dict[str, Any]]) -> tuple[list[ValidationError], list[ValidationError]]:
    """Devuelve (errors, warnings).

    errors: invalidan el bundle (sin id, id duplicado).
    warnings: estados UNKNOWN legítimos del material documental (licencia/lectura
    desconocida). Se reportan, no invalidan, conforme a la invariant del bundle
    "UNKNOWN no se oculta ni se convierte en cero/pas".
    """
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    ids = set()
    for s in sources:
        sid = s.get("source_id")
        if not sid:
            errors.append(ValidationError("SRC_NO_ID", "<source>", "source sin source_id"))
            continue
        if sid in ids:
            errors.append(ValidationError("SRC_DUPLICATE_ID", sid, f"source_id duplicado: {sid}"))
        ids.add(sid)
        # license/reading_level UNKNOWN: aviso informativo, no invalida.
        if _is_unknown(s.get("license")):
            warnings.append(
                ValidationError("SRC_LICENSE_UNKNOWN", sid, "license UNKNOWN: verificar antes de redistribuir")
            )
        if _is_unknown(s.get("reading_level")):
            warnings.append(
                ValidationError("SRC_READING_UNKNOWN", sid, "reading_level desconocido: no afirmar lectura")
            )
    return errors, warnings


def validate_operators(operators: list[dict[str, Any]], source_ids: set[str]) -> list[ValidationError]:
    errs: list[ValidationError] = []
    ids = set()
    required = [
        "operator_id", "title", "transformation", "output_requirements",
        "abstention_or_limit", "counterexample", "discriminating_test_proposal",
        "execution_status", "validation_status", "production_binding",
    ]
    for op in operators:
        oid = op.get("operator_id")
        if not oid:
            errs.append(ValidationError("OP_NO_ID", "<operator>", "operador sin operator_id"))
            continue
        if oid in ids:
            errs.append(ValidationError("OP_DUPLICATE_ID", oid, f"operator_id duplicado: {oid}"))
        ids.add(oid)
        for field in required:
            if _is_unknown(op.get(field)):
                errs.append(ValidationError("OP_MISSING_FIELD", oid, f"campo requerido ausente/UNKNOWN: {field}"))
        # source_ids deben existir en el registry
        for sid in op.get("source_ids", []):
            if sid not in source_ids:
                errs.append(ValidationError("OP_UNKNOWN_SOURCE", oid, f"source_id no registrado: {sid}"))
        # estados epistemologicos deben ser los no-ejecutados por defecto
        if op.get("execution_status") != "NOT_EXECUTED":
            errs.append(ValidationError("OP_EXEC_STATUS", oid, f"execution_status != NOT_EXECUTED: {op.get('execution_status')}"))
        if op.get("production_binding") != "NOT_WIRED":
            errs.append(ValidationError("OP_BINDING", oid, f"production_binding != NOT_WIRED: {op.get('production_binding')}"))
    return errs


def validate_cards(cards: list[dict[str, Any]], source_ids: set[str]) -> list[ValidationError]:
    errs: list[ValidationError] = []
    seen: dict[str, int] = {}
    ids: set[str] = set()
    # Dos controles independientes:
    #  - ids: todos los IDs existentes (para resolver dependencias adelantadas).
    #  - seen: conteo por ID (para detectar duplicados).
    for c in cards:
        cid = c.get("card_id")
        # Validar tipo del ID antes de incorporarlo a un set: entradas malformadas
        # (no-str) deben dar error de validación, no un traceback.
        if cid is None or not isinstance(cid, str) or not cid.strip():
            errs.append(ValidationError("CARD_BAD_ID", repr(cid), "card_id debe ser un texto no vacío"))
            continue
        seen[cid] = seen.get(cid, 0) + 1
        ids.add(cid)
        # Duplicados: se reporta una sola vez, en la segunda ocurrencia.
        if seen[cid] == 2:
            errs.append(ValidationError("CARD_DUPLICATE_ID", cid, f"card_id duplicado: {cid}"))

    for c in cards:
        cid = c.get("card_id")
        if cid is None or not isinstance(cid, str) or not cid.strip():
            continue  # ya reportado como CARD_BAD_ID arriba
        # Dependencias deben existir dentro del mismo juego de tarjetas.
        deps = c.get("depends_on", [])
        if deps is not None and not isinstance(deps, list):
            errs.append(ValidationError("CARD_BAD_DEPS", cid, "depends_on debe ser una lista"))
            deps = []
        for dep in deps or []:
            if not isinstance(dep, str):
                errs.append(ValidationError("CARD_BAD_DEP", cid, f"dependencia con tipo inválido: {dep!r}"))
            elif dep not in ids:
                errs.append(ValidationError("CARD_UNKNOWN_DEP", cid, f"dependencia no existente: {dep}"))
        # source_ids de la tarjeta deben existir.
        for sid in c.get("source_ids", []) or []:
            if sid not in source_ids:
                errs.append(ValidationError("CARD_UNKNOWN_SOURCE", cid, f"source_id no registrado: {sid}"))
        # Estados epistemológicos.
        if c.get("execution_status") != "NOT_EXECUTED":
            errs.append(ValidationError("CARD_EXEC_STATUS", cid, f"execution_status != NOT_EXECUTED: {c.get('execution_status')}"))
    # detectar ciclos simples en depends_on (DFS)
    graph: dict[str, list[str]] = {c["card_id"]: list(c.get("depends_on", []) or []) for c in cards if c.get("card_id")}
    WHITE, GREY, BLACK = 0, 1, 2
    color = {k: WHITE for k in graph}

    def dfs(node: str, stack: list[str]) -> bool:
        color[node] = GREY
        for nb in graph.get(node, []):
            if nb not in color:
                continue
            if color[nb] == GREY:
                return True
            if color[nb] == WHITE and dfs(nb, stack + [node]):
                return True
        color[node] = BLACK
        return False

    for n in graph:
        if color[n] == WHITE and dfs(n, []):
            errs.append(ValidationError("CARD_CYCLE", n, "ciclo detectado en depends_on"))
            break
    return errs


def validate_inventive_card(card: dict[str, Any]) -> list[ValidationError]:
    """Valida una ficha de conocimiento inventivo (AC-06) contra su esquema REAL.

    Esquema anidado del bundle (sección 6 del MD):
      content{operacion, mecanismo, ...}
      limits{ruptura, ...}
      discrimination{rival, observable, prediccion_mecanismo, prediccion_rival, regla, fallo}

    No se aplican defaults ni `a or b`: un campo ausente, vacío, cero o null se
    trata según su distinción. La ficha AC-06 NO usa `prueba.alternativa_explicativa`
    (ese campo pertenece al contrato del intérprete, no a la ficha).
    """
    errs: list[ValidationError] = []
    fid = card.get("ficha_id")
    fid_label = fid if isinstance(fid, str) and fid.strip() else "<ficha>"

    # identity / provenance
    if not (isinstance(fid, str) and fid.strip()):
        errs.append(ValidationError("CARD6_MISSING", fid_label, "ficha_id ausente o no texto"))
    if _is_unknown(card.get("source_id")):
        errs.append(ValidationError("CARD6_MISSING", fid_label, "source_id ausente/UNKNOWN: toda ficha precisa fuente"))

    content = card.get("content")
    if not isinstance(content, dict):
        errs.append(ValidationError("CARD6_MISSING", fid_label, "content debe ser un contenedor"))
        content = {}
    for field in ("operacion", "mecanismo"):
        if _is_unknown(content.get(field)):
            errs.append(ValidationError("CARD6_MISSING", fid_label, f"content.{field} ausente/UNKNOWN"))

    # limits.ruptura: puede estar ausente, pero si está no puede ser cero (UNKNOWN != 0)
    limits = card.get("limits")
    ruptura = limits.get("ruptura") if isinstance(limits, dict) else None
    if ruptura is not None and _is_zero(ruptura):
        errs.append(ValidationError("CARD6_RUPTURA_ZERO", fid_label, "ruptura = 0: UNKNOWN no es cero"))

    # discrimination: debe tener rival y dos predicciones DISTINTAS para discriminar
    discrimination = card.get("discrimination")
    if not isinstance(discrimination, dict):
        errs.append(ValidationError("CARD6_MISSING", fid_label, "discrimination debe ser un contenedor"))
    else:
        rival = discrimination.get("rival")
        if _is_unknown(rival):
            errs.append(ValidationError("CARD6_NO_RIVAL", fid_label, "discrimination sin rival: no discrimina"))
        pred_m = discrimination.get("prediccion_mecanismo")
        pred_r = discrimination.get("prediccion_rival")
        if _is_unknown(pred_m) or _is_unknown(pred_r):
            errs.append(ValidationError("CARD6_NO_RIVAL", fid_label, "predicciones mecanismo/rival ausentes: no discrimina"))
        elif pred_m == pred_r:
            errs.append(ValidationError("CARD6_NO_RIVAL", fid_label, "predicciones iguales: prueba no discriminante"))
    return errs


def validate_bundle(bundle_dir: Path) -> tuple[list[ValidationError], dict[str, int]]:
    """Valida toda la cola documental generada. Devuelve (errors, conteos).

    warnings (licencia/lectura UNKNOWN) no se cuentan como errores: son estados
    legítimos del material documental.
    """
    errs: list[ValidationError] = []
    counts: dict[str, int] = {}
    try:
        sources = _load_jsonl(bundle_dir / "sources" / "sources.jsonl")
        operators = _load_jsonl(bundle_dir / "operators" / "operators.jsonl")
        cards = _load_jsonl(bundle_dir / "findings" / "cards.jsonl")
    except FileNotFoundError as exc:
        return [ValidationError("BUNDLE_MISSING_FILE", str(exc), "falta archivo de cola documental")], counts

    counts = {"sources": len(sources), "operators": len(operators), "cards": len(cards)}
    source_ids = {s.get("source_id") for s in sources if s.get("source_id")}

    src_errors, _src_warnings = validate_sources(sources)
    errs += src_errors
    errs += validate_operators(operators, source_ids)
    errs += validate_cards(cards, source_ids)
    return errs, counts
