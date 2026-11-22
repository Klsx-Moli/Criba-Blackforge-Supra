"""Small paired development set derived from CBS-500; not independent gold.

References are author hypotheses about correspondence only. No reserved cases.
The source questions are snapshots, not a replacement for the corpus.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .semantic_lab import (
    Trial,
    blind_request,
    canonical,
    comparison_request,
    digest,
    direct_request,
    evaluate,
)

CORPUS_SHA256 = "c9705e139f01b6c8041f109619c03b6a835d9330296252a9e37dd5381744d968"
REFERENCE_STATUS = "PROVISIONAL_AUTHOR_REVIEW_NOT_GOLD"
# ID, query (verbatim), hypothetical intervention, corresponding metric, constraints.
PARENTS = (
    ("CBS500-01-01", (
        "¿Cómo reducir el agua fría desperdiciada al inicio de una ducha "
        "sin alterar la instalación principal?"
    ),
     (
         "Un accesorio desmontable en la salida de la ducha desvía el "
         "caudal inicial a un depósito separado hasta alcanzar la "
         "temperatura de uso; el agua recogida se reutiliza fuera de la "
         "red potable."
     ),
     (
         "Litros de agua fría que llegan al desagüe antes de alcanzar la "
         "temperatura de uso."
     ), ("sin alterar la instalación principal",)),
    ("CBS500-02-02", (
        "¿Cómo identificar aparatos que consumen electricidad "
        "innecesariamente en espera?"
    ),
     (
         "Un medidor de enchufe registra la potencia durante periodos de "
         "inactividad comprobada; se compara cada aparato con su propio "
         "patrón de funcionamiento y se señalan consumos evitables."
     ),
     (
         "Tasa de aparatos en espera innecesaria que no se identifican "
         "respecto de una medición de referencia."
     ), ()),
    ("CBS500-03-02", (
        "¿Cómo detectar plazas libres de aparcamiento sin identificar "
        "matrículas ni personas?"
    ),
     (
         "Sensores de distancia orientados al suelo dentro de cada plaza "
         "registran solamente ocupación binaria; no capturan imágenes, "
         "identificadores ni trayectorias de personas."
     ),
     (
         "Proporción de plazas clasificadas erróneamente como libres u "
         "ocupadas."
     ), ("sin identificar matrículas ni personas",)),
    ("CBS500-05-02", "¿Cómo reducir polvo durante reformas en espacios ocupados?",
     (
         "Separar la zona de obra con barreras temporales y extracción "
         "filtrada local evita que parte del polvo alcance las "
         "habitaciones ocupadas durante operaciones equivalentes."
     ),
     "Concentración de partículas en los espacios ocupados durante tareas equivalentes.", ()),
    ("CBS500-06-01", (
        "¿Cómo reducir el desgaste de una superficie deslizante sin "
        "cambiar su geometría?"
    ),
     (
         "Dosificar una película lubricante compatible con los materiales "
         "y la carga reduce el contacto directo de las asperidades sin "
         "mecanizar ni alterar la geometría de la pieza."
     ),
     (
         "Pérdida de material por ciclo de deslizamiento a igual carga y "
         "velocidad."
     ), ("sin cambiar su geometría",)),
    ("CBS500-07-02", (
        "¿Cómo detectar estrés hídrico de plantas sin confundirlo con "
        "falta de nutrientes?"
    ),
     (
         "Combinar humedad del sustrato con respuesta térmica foliar tras "
         "una reposición controlada de agua y contrastar con parcelas de "
         "referencia nutricional permite separar ambos factores bajo "
         "condiciones definidas."
     ),
     (
         "Tasa de confusión entre estrés hídrico y déficit nutricional en "
         "controles conocidos."
     ), ("sin confundirlo con falta de nutrientes",)),
    ("CBS500-08-01", (
        "¿Cómo reducir desperdicio de alimentos en un comedor con "
        "asistencia variable?"
    ),
     (
         "Preparar un lote inicial pequeño y escalonar lotes posteriores "
         "según llegadas observadas limita sobrantes sin depender de una "
         "previsión puntual de asistencia."
     ),
     "Kilogramos de alimento preparado no consumido por cien comensales a igual servicio.", ()),
    ("CBS500-09-02", "¿Cómo reducir segundas visitas por errores de registro de datos de entrada?",
     (
         "Una comprobación previa de campos obligatorios detecta ausencias "
         "antes de confirmar la cita y permite corregir el registro en la "
         "primera visita."
     ),
     "Segundas visitas debidas a registros incompletos por cien citas.", ()),
    ("CBS500-13-01", "¿Cómo distinguir ausencia de medición de un valor realmente igual a cero?",
     (
         "Guardar la lectura junto a un indicador explícito de validez "
         "separa un cero observado de una lectura ausente; las "
         "agregaciones conservan ambos estados sin imputar ceros."
     ),
     "Tasa de lecturas ausentes clasificadas como ceros observados.", ()),
    ("CBS500-14-01", (
        "¿Cómo detectar faltantes de inventario cuando existen "
        "movimientos todavía no registrados?"
    ),
     (
         "Un diario separado de movimientos pendientes con identificadores "
         "de operación permite reconciliar el conteo físico contra el "
         "saldo registrado más los movimientos aún no asentados."
     ),
     "Tasa de falsos faltantes tras reconciliar movimientos pendientes y conteos físicos.", ()),
    ("CBS500-21-01", (
        "¿Cómo mejorar disipación térmica de componentes electrónicos en "
        "una carcasa compacta?"
    ),
     (
         "Un repartidor térmico conduce calor desde el componente hacia "
         "una superficie mayor de la carcasa, siempre que exista contacto "
         "térmico adecuado y una vía de disipación exterior."
     ),
     "Tiempo por encima de una temperatura límite del componente bajo carga equivalente.", ()),
    ("CBS500-20-03", (
        "¿Cómo distinguir vibración producida por desequilibrio de la "
        "causada por una fijación floja?"
    ),
     (
         "Comparar espectros y fase a velocidades controladas junto con "
         "una inspección de fijaciones en estado seguro permite contrastar "
         "patrones de desequilibrio y holgura sin inferir la causa de un "
         "único pico."
     ),
     "Tasa de diagnósticos de vibración incorrectos frente a fallos de referencia conocidos.", ()),
)


def _proposal(mechanism: str, metric: str, claims: tuple[str, ...]) -> dict[str, Any]:
    # Only correspondence is labelled. These are hypothetical, uncalibrated trials.
    return {
        "pertinencia": "PERTINENTE", "hipotesis": mechanism, "mecanismo": mechanism,
        "cadena_causal": [mechanism, "Contrastar la variación de la métrica frente al control."],
        "prueba_concreta": "Comparar grupos o situaciones equivalentes con y sin la intervención.",
        "prueba": {"metrica": metric, "baseline": "Misma situación sin intervención.",
                   "umbral": "Reducción ilustrativa del 10%; NO calibrada.",
                   "condicion_fracaso": "No se observa una reducción respecto al control.",
                   "alternativa_explicativa": "Cambio simultáneo de condiciones no controlado.",
                   "resultado_favorable_mecanismo": "Reducción con condiciones equivalentes.",
                   "resultado_favorable_alternativa": "Reducción solo al cambiar las condiciones."},
        "supuestos": ["Caso hipotético; las precondiciones reales requieren revisión."],
        "aportacion_por_tecnica": ["Intervención propuesta.", "Comparación controlada."],
        "conocimiento_previo": [], "evidencia_citada": [],
        "incertidumbre": "No se ha verificado eficacia, seguridad, factibilidad ni novedad.",
        "novedad": "No evaluada.",
        "comprobacion_restricciones": [{"restriccion": r, "estado": "CUMPLE",
                                         "justificacion": (
                                             "Declaración no verificada del productor."
                                         )}
                                        for r in claims],
    }


def cases() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(parent: tuple[Any, ...], variant: str, data: dict[str, Any], label: str,
            reason: str, donor: str) -> None:
        pid, query, _, _, restrictions = parent
        rows.append({"id": f"{pid}:{variant}", "parent_id": pid, "query": query,
                     "restrictions": list(restrictions), "proposal": data, "reference": label,
                     "reason": reason, "donor_id": donor, "split": "development",
                     "reference_status": REFERENCE_STATUS, "corpus_sha256": CORPUS_SHA256})

    for i, parent in enumerate(PARENTS):
        pid, query, mechanism, metric, restrictions = parent
        donor_id, _, other_mechanism, other_metric, _ = PARENTS[(i + 1) % len(PARENTS)]
        good = _proposal(mechanism, metric, restrictions)
        wrong = _proposal(other_mechanism, other_metric, restrictions)
        add(parent, "aligned", good, "SUPPORT",
            "Intervención y métrica corresponden al objetivo; eficacia no evaluada.", pid)
        add(parent, "swap", wrong, "REJECT",
            "Intervención y métrica responden al problema donante, no al destinatario.", donor_id)
        decoy = deepcopy(wrong)
        decoy["hipotesis"] = f"Se declara que resuelve: {query} {decoy['hipotesis']}"
        add(parent, "lexical", decoy, "REJECT",
            "Copiar la pregunta no transforma el mecanismo ni la métrica del donante.", donor_id)
        metric_swap = deepcopy(good)
        metric_swap["prueba"]["metrica"] = other_metric
        add(parent, "metric", metric_swap, "REJECT",
            "El mecanismo parece pertinente, pero la métrica no evalúa el objetivo.", donor_id)
    # Explicit transfer control for the reported administrative/ducha contradiction.
    water = PARENTS[0]
    _, _, _, water_metric, water_restrictions = water
    add(water, "transfer", _proposal(
        (
            "Adaptar el principio de prevención de errores de registros a un "
            "acoplamiento mecánico codificado: solo permite conectar el "
            "accesorio desmontable de derivación al depósito separado, "
            "evitando enviar el caudal frío al desagüe por una conexión "
            "equivocada."
        ),
        water_metric, water_restrictions), "SUPPORT",
        "El principio administrativo se transforma en una intervención sobre el caudal de agua.",
        "CBS500-09-02")
    admin = PARENTS[7]
    wrong_admin = _proposal(admin[2], admin[3], water_restrictions)
    add(water, "incident", wrong_admin, "REJECT",
        (
            "Caso del incidente: restricciones de ducha declaradas, mecanismo "
            "administrativo."
        ), admin[0])
    padded = deepcopy(wrong_admin)
    padded["hipotesis"] = water[1] + " " + padded["hipotesis"]
    add(water, "incident-lexical", padded, "REJECT",
        "La inclusión literal de la pregunta no subsana la incongruencia.", admin[0])
    for index, donor_id, mechanism in (
        (2, "CBS500-14-01", (
            "Trasladar un tablero de inventario de ubicaciones a plazas: cada "
            "sensor de distancia entrega únicamente ocupación binaria de su "
            "plaza, con reconciliación periódica de estados sin imágenes ni "
            "identificadores."
        )),
        (8, "CBS500-09-02", (
            "Adaptar el control de campos obligatorios al registro de "
            "sensores: guardar una bandera de lectura presente y mantener un "
            "cero medido distinto de un campo ausente; no rellenar ausencias."
        )),
        (10, "CBS500-05-02", (
            "Adaptar el principio de extracción localizada de polvo a la ruta "
            "del calor: conducir energía térmica desde el componente hacia un "
            "repartidor conectado a la carcasa, con disipación exterior bajo "
            "una carga controlada."
        )),
    ):
        parent = PARENTS[index]
        add(parent, "transfer", _proposal(mechanism, parent[3], parent[4]), "SUPPORT",
            (
                "El principio donante se transforma en una intervención "
                "específica del destinatario."
            ), donor_id)
    for i in (0, 2, 5, 10):
        parent = PARENTS[i]
        pid, _, _, metric, restrictions = parent
        add(parent, "unknown", _proposal(
            (
                "Un controlador sin arquitectura especificada modifica una "
                "condición todavía no identificada; falta describir la "
                "intervención y sus precondiciones."
            ), metric, restrictions),
            "UNRESOLVED", (
                "No hay vínculo causal suficiente para confirmar ni refutar una "
                "intervención concreta."
            ), pid)
    return rows


def trial_for(case_id: str, run_id: str) -> Trial:
    case = next((row for row in cases() if row["id"] == case_id), None)
    if case is None:
        raise ValueError("unknown development case")
    return Trial(case["id"], run_id, f"{run_id}:{case['id']}", case["id"],
                 "synthetic-author-not-model", case["query"], tuple(case["restrictions"]),
                 canonical(case["proposal"]), digest({"corpus": CORPUS_SHA256,
                     "parent_id": case["parent_id"], "query": case["query"],
                     "restrictions": case["restrictions"]}))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("list", "references", "direct", "blind", "compare", "evaluate")
    )
    parser.add_argument("--case")
    parser.add_argument("--run")
    parser.add_argument("--reviewer")
    parser.add_argument("--attempt")
    parser.add_argument("--blind-reviewer")
    parser.add_argument("--blind-attempt")
    parser.add_argument("--blind-receipt", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if args.action in ("list", "references"):
        keys = ("id", "parent_id", "query", "split") if args.action == "list" else (
            "id", "reference", "reason", "reference_status", "donor_id", "corpus_sha256")
        result: Any = [{key: row[key] for key in keys} for row in cases()]
    else:
        if not all((args.case, args.run, args.reviewer, args.attempt)):
            parser.error("--case, --run, --reviewer, --attempt are required")
        try:
            trial = trial_for(args.case, args.run)
            blind = None
            blind_raw = None
            if args.action == "blind":
                request = blind_request(trial, args.reviewer, args.attempt)
            elif args.action == "compare" or (args.action == "evaluate" and args.blind_receipt):
                if not all((args.blind_reviewer, args.blind_attempt, args.blind_receipt)):
                    parser.error("blind reviewer, attempt and receipt are required")
                blind = blind_request(trial, args.blind_reviewer, args.blind_attempt)
                blind_raw = args.blind_receipt.read_text(encoding="utf-8")
                request = comparison_request(trial, blind, blind_raw, args.reviewer, args.attempt)
            else:
                request = direct_request(trial, args.reviewer, args.attempt)
            if args.action == "evaluate":
                raw = args.receipt.read_text(encoding="utf-8") if args.receipt else None
                result = evaluate(trial, request, raw, blind=blind, blind_receipt=blind_raw)
            else:
                result = {**asdict(request), "request_sha256": request.sha256}
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 2 if args.action == "evaluate" and result["outcome"] in (
        "EVALUATOR_ERROR", "NOT_EVALUATED") else 0


if __name__ == "__main__":
    raise SystemExit(main())
