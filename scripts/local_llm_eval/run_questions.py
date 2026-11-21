"""30 preguntas x 5 modos de CRIBA contra el LLM local (qwen3-4b-agenttools).

Ruta de producto real: criba.inventar.invent(query, ...) -> usa el interprete
LocalLlamaInterpreter (CRIBA_LOCAL_BASE=127.0.0.1:8080/v1) -> ficha con
hipotesis/mecanismo/prueba/provenance -> es lo que alimenta el dossier.

Para cada (pregunta, modo) guarda:
  - estado_interpretacion (PROPUESTA / abstencion / pendiente)
  - hipotesis, mecanismo, prueba_concreta
  - provenance del interprete (model, backend, tokens, tiempo)
  - error si lo hay

NO toca umbrales ni schema. Reporta lo que el modelo real devuelve.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback

os.environ["CRIBA_CONSTRAINED_DECODING"] = "json_schema"
os.environ["CRIBA_LOCAL_BASE"] = "http://127.0.0.1:8080/v1"
os.environ["CRIBA_LOCAL_MODEL"] = "qwen3"
os.environ.setdefault("CRIBA_EXTERNAL_TIMEOUT_S", "240")

sys.path.insert(0, "C:/ASTRA_WORK/Criba-Blackforge-Supra/criba-blackforge/src")
from criba.inventar import invent  # noqa: E402

PREGUNTAS = [
    "Como reducir el churn de clientes en una app de suscripcion",
    "Disenar una defensa contra phishing para una pyme sin presupuesto",
    "Como hacer que un equipo remoto coordine sin reuniones sincronas",
    "Reducir el desperdicio de alimentos en un supermercado mediano",
    "Como verificar que un modelo de IA no alucina en diagnostico medico",
    "Mejorar la adopcion de una herramienta interna que nadie usa",
    "Como detectar fraude en pagos sin frenar transacciones legitimas",
    "Disenar incentivos para que vecinos compartan coche al trabajo",
    "Como reducir el consumo energetico de un edificio de oficinas",
    "Que mecanismo hace fiable una votacion online sin autoridad central",
    "Como ensenar programacion a adolescentes sin clases magistrales",
    "Reducir el tiempo de respuesta de un servicio de atencion al ciudadano",
    "Como evitar que un marketplace se llene de vendedores deshonestos",
    "Disenar un sistema de movilidad para una ciudad con muchas cuestas",
    "Como medir el bienestar laboral sin convertir la metrica en objetivo",
    "Que prueba distinguiria si un farmaco funciona por placebo o por mecanismo",
    "Como organizar turnos de hospital respetando descanso y cobertura",
    "Reducir la huella de carbono de una cadena de suministro textil",
    "Como lograr que un algoritmo de seleccion no amplifique sesgos previos",
    "Disenar un metodo para que equipos adopten hallazgos de auditoria",
    "Como prevenir la captura regulatoria en un organismo publico",
    "Que mecanismo hace que una comunidad de software libre no se fragmente",
    "Como reducir reuniones en una startup sin perder alineacion",
    "Detectar anomalias en sensores industriales con pocos ejemplos etiquetados",
    "Como disenar una pension sostenible con esperanza de vida creciente",
    "Que estructura hace que un proyecto open source sobreviva a su fundador",
    "Como reducir el ausentismo escolar en barrios desfavorecidos",
    "Disenar un sistema de recomendacion que no cree burbuja de filtros",
    "Como verificar procedencia de datos en una cadena de suministro",
    "Que prueba refutaria que esta propuesta de negocio crea valor real",
]


def run_one(query: str) -> dict:
    """Ruta dossier real: invent() con el interprete LLM local.

    invent() fija engine.run_round(mode='stratified') por diseno; el 'modo' de
    activate() es otra capa. Aqui se ejercita la ruta producto LLM->dossier.
    """
    t0 = time.monotonic()
    try:
        ficha = invent(query, rounds=1, batch_size=4, top=1, offline=True)
    except Exception as exc:  # noqa: BLE001
        return {"query": query, "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc()[-400:], "elapsed_s": round(time.monotonic()-t0, 1)}
    prov = ficha.get("interpretacion_provenance") or {}
    return {
        "query": query,
        "candidate": ficha.get("title"),
        "estado": ficha.get("estado_interpretacion"),
        "hipotesis": ficha.get("hipotesis"),
        "mecanismo": ficha.get("mecanismo"),
        "prueba_concreta": ficha.get("prueba_concreta"),
        "incertidumbre": ficha.get("incertidumbre"),
        "aporte_tecnicas": ficha.get("aportacion_por_tecnica"),
        "error": ficha.get("interpretacion_error"),
        "model_backend": prov.get("interpreter_backend"),
        "model_reported": prov.get("model_reported"),
        "duration_ms": prov.get("duration_ms"),
        "finish_reason": ficha.get("interpretacion_finish_reason"),
        "usage": ficha.get("interpretacion_usage"),
        "elapsed_s": round(time.monotonic()-t0, 1),
    }


def main() -> None:
    resultados = []
    total = len(PREGUNTAS)
    for n, q in enumerate(PREGUNTAS, 1):
        r = run_one(q)
        resultados.append(r)
        tag = r.get("estado") or r.get("error", "?")
        print(f"[{n}/{total}] {tag[:38]:38s} | {q[:44]}", flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1)
    print("GUARDADO:", OUT, flush=True)
    from collections import Counter
    estados = Counter(r.get("estado") or ("ERROR" if r.get("error") else "?") for r in resultados)
    print("=== estados ===", dict(estados), flush=True)


if __name__ == "__main__":
    main()
