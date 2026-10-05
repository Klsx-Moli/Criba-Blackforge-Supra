"""Sentinelas de los defectos de auditoría: ninguna falla se convierte en validación."""

from __future__ import annotations

import json
import sqlite3

import httpx
import pytest
from criba.constants import FEATURES
from criba.interprete import openai_compatible as oc
from criba.interprete.banco import CASOS, evaluar_banco
from criba.interprete.contrato import PROMPT_VERSION, SCHEMA_VERSION, validar_propuesta
from criba.interprete.pipeline import build_interprete_block
from criba.interprete.prefilter import PreFilter, sota_taboo_violations
from criba.interprete.protocolo import protocolo_para
from criba.interprete.puerto import InterpretationResult
from criba.interprete.store import InterpreteStore
from criba.storage import Storage

from verification.interpreter_cases import critica, propuesta, resultado

IDEA = {
    "id": "c1",
    "method1": "Poka-Yoke",
    "method2": "Retroalimentación",
    "description": "Revisar campos ausentes antes de confirmar citas.",
    "causal_axes_changed": ["flujo", "feedback"],
    "convergence": {"novelty": 0.75},
}


def respuesta(data, *, status=200, model="reportado"):
    return httpx.Response(
        status,
        json={
            "model": model,
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(data)}}],
        },
    )


def transporte(monkeypatch, responses):
    enviados = []

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json=None, headers=None):
            enviados.append((url, json))
            response = responses[len(enviados) - 1]
            if isinstance(response, Exception):
                raise response
            return response

    monkeypatch.setattr(oc.httpx, "Client", Client)
    return enviados


@pytest.mark.parametrize(
    "key,value",
    [
        ("mecanismo", None),
        ("mecanismo", "None"),
        ("hipotesis", None),
        ("supuestos", "cada carácter"),
        ("supuestos", [None]),
        ("aportacion_por_tecnica", "ab"),
        ("cadena_causal", ["solo una etapa"]),
        ("prueba", {}),
        ("prueba", None),
        ("evidencia_citada", [1]),
        ("evidencia_citada", [True]),
        ("pertinencia", None),
        ("incertidumbre", ""),
        ("comprobacion_restricciones", "sin restricciones"),
        ("score", 0.99),
        ("ruta_desbloqueo", None),
    ],
)
def test_esquema_corrupto_no_pasa(key, value, monkeypatch):
    data = propuesta()
    data[key] = value
    enviados = transporte(monkeypatch, [respuesta(data)])
    result = oc.OpenAICompatibleInterpreter().proponer("colas", IDEA)
    assert not result.es_propuesta
    assert result.error.startswith("validacion:")
    assert len(enviados) == 1, "la crítica no consume llamadas para un esquema inválido"
    assert result.provenance and result.provenance.raw_output_sha256


def test_propuesta_y_critica_son_llamadas_distintas_con_procedencia(monkeypatch):
    enviados = transporte(monkeypatch, [respuesta(propuesta()), respuesta(critica(), model="c")])
    result = oc.OpenAICompatibleInterpreter(model="p", critic_model="c").proponer("colas", IDEA)
    assert result.es_propuesta, result.error
    assert [e[1]["model"] for e in enviados] == ["p", "c"]
    assert result.model_requests == 2
    assert result.critica["provenance"]["model_requested"] == "c"
    assert result.critica["provenance"]["prompt_sha256"] != result.provenance.prompt_sha256
    assert result.critica["independent_validation"] is False
    assert result.provenance.prompt_version == PROMPT_VERSION
    assert "score" not in result.to_campos()


@pytest.mark.parametrize(
    "key,value",
    [
        ("fiel_evidencia", False),
        ("falsable", "true"),
        ("intercambio_tecnicas_generico", True),
        ("objeciones", ["cita inventada"]),
        ("respuestas_epistemologicas", {"Q1": "factor"}),
        ("score", 0.99),
    ],
)
def test_critica_no_aprobatoria_degrada_a_pendiente(monkeypatch, key, value):
    data = critica()
    data[key] = value
    transporte(monkeypatch, [respuesta(propuesta()), respuesta(data)])
    result = oc.OpenAICompatibleInterpreter().proponer("colas", IDEA)
    assert not result.es_propuesta and "critica." in result.error
    assert result.critica["evaluation_status"] == "REJECTED"
    assert result.raw_output and result.critica["raw_output"]


def test_critica_sin_red_no_aprueba(monkeypatch):
    transporte(monkeypatch, [respuesta(propuesta()), httpx.ReadTimeout("token=secret")])
    result = oc.OpenAICompatibleInterpreter().proponer("colas", IDEA)
    assert result.error == "critica_no_disponible:timeout"
    assert result.model_requests == 2
    assert "secret" not in result.error
    assert result.critica["evaluation_status"] == "NOT_EVALUATED"


def test_abstencion_es_explicita_y_no_necesita_relleno(monkeypatch):
    enviados = transporte(
        monkeypatch,
        [respuesta({"pertinencia": "ABSTENER", "motivo_abstencion": "cruce irrelevante"})],
    )
    result = oc.OpenAICompatibleInterpreter().proponer("colas", IDEA)
    assert result.pertinencia == "ABSTENER" and not result.es_propuesta
    assert len(enviados) == 1
    assert result.error == "validacion:abstencion:cruce irrelevante"


def test_abstencion_sin_motivo_no_cuenta_como_respuesta_correcta(monkeypatch):
    transporte(monkeypatch, [respuesta({"pertinencia": "ABSTENER"})])
    r = oc.OpenAICompatibleInterpreter().proponer("colas", IDEA)
    assert r.error == "validacion:abstencion_sin_motivo"
    report = evaluar_banco(lambda *args: r)
    assert report["correct_abstention_rate"] == 0


def test_citas_restricciones_y_umbral_se_comprueban():
    data = propuesta()
    data["evidencia_citada"] = [1]
    assert validar_propuesta(data, IDEA, [{"title": "e"}]) == []
    assert validar_propuesta(data, IDEA, [])
    data["evidencia_citada"] = []
    data["prueba"]["umbral"] = "mejor que antes"
    assert "prueba.umbral requiere un valor numérico" in validar_propuesta(data, IDEA, [])
    data = propuesta()
    bloqueada = {**IDEA, "bloqueo": {"restricciones_obligatorias": ["misma calidad"]}}
    assert validar_propuesta(data, bloqueada, [])
    data["comprobacion_restricciones"] = [
        {"restriccion": "misma calidad", "estado": "VIOLA", "justificacion": "reduce calidad"}
    ]
    assert "restriccion violada o no verificada" in validar_propuesta(data, bloqueada, [])


def test_predicciones_identicas_no_son_prueba_discriminante():
    data = propuesta()
    data["prueba"]["resultado_favorable_alternativa"] = data["prueba"][
        "resultado_favorable_mecanismo"
    ]
    assert "prueba.predicciones_no_discriminantes" in validar_propuesta(data, IDEA, [])


def test_etiqueta_propusta_no_acredita_critica_completa():
    r = InterpretationResult(estado="PROPUESTA", mecanismo=propuesta()["mecanismo"])
    assert not r.es_propuesta
    assert "crítica" in r.to_campos()["error"]


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'])
def test_json_ambiguo_o_no_finito_se_rechaza(raw):
    with pytest.raises(ValueError):
        oc._extraer_json(raw)


def test_configuracion_invalida_conserva_procedencia_sin_peticion(monkeypatch):
    monkeypatch.setenv("CRIBA_EXTERNAL_MAX_TOKENS", "incorrecto")
    r = oc.OpenAICompatibleInterpreter().proponer("colas", IDEA)
    assert not r.es_propuesta and r.model_requests == 0 and r.provenance
    assert r.error == "configuracion_invalida:max_tokens"


def test_mecanismo_no_puede_repetir_nombre_de_tecnica():
    data = propuesta()
    data["mecanismo"] += " Se aplica Poka-Yoke a los registros."
    assert "mecanismo repite nombres de técnicas" in validar_propuesta(data, IDEA, [])


def test_mencionar_factor_dominio_o_tiempo_no_responde_preguntas():
    protocolo = protocolo_para({"description": "factor anomalía dominio temporal"})
    assert protocolo["count_pending"] == 11
    assert protocolo["count_auto"] == 0


def test_prefiltro_aísla_entradas_invalidas_preserva_orden_y_respeta_limites():
    ideas = [
        {**IDEA, "id": "primera", "convergence": {"value_score": 0.1}},
        {"id": "sin-description"},
        {**IDEA, "id": "segunda", "convergence": {"value_score": 1}},
    ]
    result = PreFilter().apply(ideas)
    assert [i["id"] for i in result["candidates"]] == ["primera", "segunda"]
    assert result["stats"]["invalid_rejected"] == 1
    assert PreFilter(dh_lo=0.60, dh_hi=0.62).apply([IDEA])["candidates"] == []
    assert (
        PreFilter(strict=False).apply([{**IDEA, "convergence": {"novelty": 0.4}}])["candidates"]
        == []
    )
    assert PreFilter(strict=False).apply([{**IDEA, "convergence": {}}])["candidates"] == []
    assert sota_taboo_violations({"description": "prestatic_firewallpost"}) == []
    assert sota_taboo_violations({"description": "static_firewall"}) == ["static_firewall"]


def decision(*, accepted=False, error="timeout"):
    return {
        "id": "c1",
        "description": "input",
        "interprete_score": None,
        "interprete_verdict": "PROPUESTA" if accepted else "PENDIENTE_INTERPRETACION",
        "interprete_evaluation_status": "CRITIQUED" if accepted else "NOT_EVALUATED",
        "interprete_analisis": "" if accepted else error,
        "interprete_result": resultado().to_campos() if accepted else {"error": error},
        "interprete_raw_output": "salida del modelo",
        "interprete_provenance": {
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "raw_output_sha256": "h",
            "fallback_used": False,
        },
    }


def test_store_reintenta_pendiente_guarda_salida_procedencia_y_null(tmp_path):
    storage = Storage(str(tmp_path / "s.db"))
    store = InterpreteStore(storage)
    args = {"activation_id": "a", "modelo": "m", "run_id": "r", "seed": None}
    assert store.record_decision(idea=decision(), **args)["status"] == "recorded"
    assert store.record_decision(idea=decision(accepted=True), **args)["status"] == "retried"
    assert store.record_decision(idea=decision(accepted=True), **args)["status"] == "deduplicated"
    row = store.get_verdict("c1", "m", run_id="r", seed=None)
    assert row["epistemic_score"] is None and row["evaluation_status"] == "CRITIQUED"
    assert row["response"]["interpretation"]["interprete_raw_output"] == "salida del modelo"
    assert row["provenance"]["prompt_version"] == PROMPT_VERSION
    assert store.get_verdict("c1", "m", run_id="r", seed=0) is None
    assert store.record_decision(idea=decision(), **{**args, "seed": 0})["status"] == "recorded"
    assert (
        store.record_decision(idea=decision(error="429"), **{**args, "run_id": "r2"})["status"]
        == "recorded"
    )
    assert store.get_verdict("c1", "m", run_id="r", seed=None)["evaluation_status"] == "CRITIQUED"
    assert store.get_verdict("c1", "m")["run_id"] == "r2"
    con = storage.connect()
    try:
        assert con.execute("SELECT count(*) FROM interprete_attempts").fetchone()[0] == 4
    finally:
        con.close()


def test_store_es_atomico_si_falla_escritura(tmp_path):
    storage = Storage(str(tmp_path / "s.db"))
    store = InterpreteStore(storage)
    args = {"activation_id": "a", "modelo": "m", "run_id": "r", "seed": 1}
    store.record_decision(idea=decision(), **args)
    con = storage.connect()
    with con:
        con.execute(
            "CREATE TRIGGER fail_write BEFORE INSERT ON interprete_decisions "
            "BEGIN SELECT RAISE(ABORT, 'disk failure'); END"
        )
    con.close()
    with pytest.raises(sqlite3.IntegrityError):
        store.record_decision(idea=decision(accepted=True), **args)
    assert store.get_verdict("c1", "m", run_id="r", seed=1)["evaluation_status"] == "NOT_EVALUATED"
    con = storage.connect()
    assert con.execute("SELECT count(*) FROM interprete_attempts").fetchone()[0] == 1
    con.close()


@pytest.mark.parametrize(
    "corrupcion", [None, "critica_invalida", "version_antigua", "json_truncado"]
)
def test_cache_se_revalida_y_el_pendiente_no_congela_intento(monkeypatch, tmp_path, corrupcion):
    from criba.interprete.juez import JuezInterprete

    enviados = transporte(
        monkeypatch,
        [
            respuesta(propuesta()),
            respuesta(critica()),
            respuesta(propuesta()),
            respuesta(critica()),
        ],
    )
    storage = Storage(str(tmp_path / "cache.db"))
    juez = JuezInterprete(storage=storage, interpreter=oc.OpenAICompatibleInterpreter(model="m"))
    primero = juez.interpretar_lote("colas", [IDEA], "a", "r", 1)
    assert primero["interpretados"][0]["interprete_verdict"] == "PROPUESTA"
    if corrupcion:
        con = storage.connect()
        with con:
            if corrupcion == "version_antigua":
                con.execute("UPDATE interprete_decisions SET schema_version='propuesta-1'")
            elif corrupcion == "json_truncado":
                con.execute("UPDATE interprete_decisions SET response_json='{truncado'")
            else:
                raw = con.execute("SELECT response_json FROM interprete_decisions").fetchone()[0]
                data = json.loads(raw)
                data["interpretation"]["interprete_result"]["critica"]["respuesta"] = "corrupta"
                con.execute("UPDATE interprete_decisions SET response_json=?", (json.dumps(data),))
        con.close()
    segundo = juez.interpretar_lote("colas", [IDEA], "a", "r", 1)
    registro = segundo["interpretados"][0]["_registro"]["status"]
    assert registro == ("retried" if corrupcion else "deduplicated")
    assert len(enviados) == (4 if corrupcion else 2)


def test_escritura_concurrente_no_duplica_exito_y_conserva_identidad(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    storage = Storage(str(tmp_path / "concurrent.db"))
    store = InterpreteStore(storage)

    def write(_):
        return store.record_decision(
            activation_id="a", idea=decision(accepted=True), modelo="m", run_id="r", seed=None
        )["status"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        estados = list(pool.map(write, range(8)))
    assert estados.count("recorded") == 1 and estados.count("deduplicated") == 7
    con = storage.connect()
    assert con.execute("SELECT count(*) FROM interprete_decisions").fetchone()[0] == 1
    con.close()


def test_migracion_preserva_archivo_legacy_sin_convertir_desconocido_en_cero(tmp_path):
    storage = Storage(str(tmp_path / "old.db"))
    con = storage.connect()
    with con:
        con.execute(
            "CREATE TABLE interprete_decisions (combo_key TEXT, run_id TEXT, seed INTEGER, "
            "activation_id TEXT, idea_id TEXT, modelo TEXT, labels_json TEXT, "
            "epistemic_score REAL NOT NULL, veredicto TEXT, response_json TEXT, "
            "created_at TEXT, PRIMARY KEY(combo_key, run_id, seed))"
        )
        con.execute(
            "INSERT INTO interprete_decisions VALUES "
            "('c1::m','r',NULL,'a','c1','m','[]',0.0,'PENDIENTE','{}','t')"
        )
    con.close()
    store = InterpreteStore(storage)
    row = store.get_verdict("c1", "m", run_id="r", seed=None)
    assert row["epistemic_score"] is None
    assert row["evaluation_status"] == "LEGACY_UNVERIFIED"
    con = storage.connect()
    assert (
        con.execute("SELECT epistemic_score FROM interprete_decisions_legacy_v1").fetchone()[0]
        == 0.0
    )
    con.close()
    InterpreteStore(storage)  # idempotent migration


def test_pipeline_registra_tipo_sin_filtrar_secretos(monkeypatch, caplog):
    monkeypatch.setitem(FEATURES, "interprete_serendipia", True)
    monkeypatch.setattr(
        "criba.interprete.pipeline.JuezInterprete",
        lambda **kw: (_ for _ in ()).throw(ValueError("Bearer SECRET")),
    )
    result = build_interprete_block("q", [IDEA], {})
    assert result["error_type"] == "ValueError"
    assert result["evaluation_status"] == "NOT_EVALUATED"
    assert "SECRET" not in caplog.text


def test_banco_no_confunde_fallo_de_red_con_abstencion():
    report = evaluar_banco(
        lambda *args: InterpretationResult(estado="PENDIENTE_INTERPRETACION", error="timeout")
    )
    assert not report["passed"]
    assert report["correct_abstention_rate"] == 0
    assert report["schema_response_rate"] == 0


def test_banco_exige_positivos_negativos_y_consistencia():
    def proponer(query, *args):
        if query == CASOS[0]["query"]:
            return resultado()
        return InterpretationResult(
            estado="PENDIENTE_INTERPRETACION",
            pertinencia="ABSTENER",
            error="validacion:abstencion:incompatible",
        )

    report = evaluar_banco(proponer, referencia=proponer)
    assert report["passed"] and report["reference_agreement"] == 1
    assert report["correct_abstention_rate"] == report["consistency_rate"] == 1
    with pytest.raises(ValueError):
        evaluar_banco(proponer, repeticiones=1)


def test_local_rechaza_endpoint_remoto_y_no_envia_credenciales(monkeypatch):
    local = oc.LocalLlamaInterpreter(base_url="https://api.nousresearch.com/v1")
    assert local.operativo()[0] is False
    assert local.proponer("q", IDEA).model_requests == 0
    assert "Authorization" not in local._headers()


def test_local_no_esta_operativo_solo_por_models(monkeypatch):
    monkeypatch.setattr(
        oc.OpenAICompatibleInterpreter, "operativo", lambda self: (True, "catalogo")
    )
    monkeypatch.setattr(
        oc.OpenAICompatibleInterpreter,
        "proponer",
        lambda *args: InterpretationResult(estado="PENDIENTE_INTERPRETACION", error="timeout"),
    )
    local = oc.LocalLlamaInterpreter()
    assert not local.operativo()[0]
    assert local.gate_report and not local.gate_report["passed"]


def test_inventar_reutiliza_critica_y_dossier_recibe_prueba_declarada():
    from criba.inventar import _judge
    from criba.supra_dossier import preparar_dossier

    judge = _judge(
        "q", {"critica": {"evaluation_status": "CRITIQUED", "respuesta": critica()}}, False
    )
    assert judge["score"] is None and judge["evaluation_status"] == "CRITIQUED"
    entry = {**propuesta(), "candidate_id": "c", "run_id": "r"}
    dossier = preparar_dossier(entry, "colas")
    for field, src in (
        ("metrica", "metrica"),
        ("comparacion", "baseline"),
        ("regla_decision", "umbral"),
        ("condicion_fracaso", "condicion_fracaso"),
    ):
        assert dossier["prueba_discriminante"][field] == entry["prueba"][src]
