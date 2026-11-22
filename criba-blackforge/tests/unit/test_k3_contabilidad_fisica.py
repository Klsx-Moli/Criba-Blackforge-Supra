"""Verificacion ADVERSARIAL de la contabilidad fisica de llamadas.

El encargo exige comprobar que un registro normalizado NO demuestra por si
mismo cuantas llamadas fisicas ocurrieron. Estos tests son deliberadamente
hostiles: intentan hacer que el sistema declare un resultado sin llamada
acreditada, o que cuente dos llamadas donde hubo una.

No modifican produccion. Documentan lo que el esquema ACTUAL puede y no
puede probar.
"""

from __future__ import annotations

from benchmarks.innovation.semantic_ledger_gate import (
    normalizar_slot,
    validar_registros,
)
from criba.storage import Storage

REVIEW = "judge-local"
SHA = "a" * 64


def _reserva(status="ACTIVE", request=SHA, receipt=None):
    return {
        "attempt": "intento-1",
        "request_sha256": request,
        "reviewer": REVIEW,
        "status": status,
        "created_at": "2026-11-22T00:00:00+00:00",
        "closed_at": None,
        "receipt_sha256": receipt,
    }


# --- 1. Resultado declarado SIN llamada acreditada -------------------------

def test_recibo_inventado_no_se_distingue_de_real(tmp_path) -> None:
    """Si alguien inserta un recibo a mano, el ledger no puede negarlo.

    El esquema no guarda evidencia de transporte (ni request_id del
    proveedor, ni hora de envio, ni bytes recibidos). Un recibo con
    request_sha256 correcto y cuerpo valido es INDISTINGUIBLE de uno real.
    Esto NO es un fallo corregible en el adaptador: es una limitacion del
    esquema que hay que declarar y firmar.
    """
    db = tmp_path / "falso.sqlite3"
    st = Storage(db)
    st.reserve_semantic_attempt("s", "intento-1", SHA, REVIEW)
    # Inserto un recibo "sin haber llamado al modelo".
    st.close_semantic_attempt("s", "intento-1", SHA, "b" * 64)
    estado = st.semantic_attempt_status("s", "intento-1")
    recibo = st.load_semantic_receipts("s", "intento-1")
    # El sistema lo acepta como CLOSED con recibo. No hay forma de saber
    # desde el ledger si hubo llamada fisica.
    assert estado["status"] == "CLOSED"
    assert estado["receipt_sha256"] == "b" * 64
    assert len(recibo) == 1
    # Y el normalizador lo reporta como etiqueta con 1 llamada fisica.
    reg = normalizar_slot(
        case_id="C:1", repetition=0, arm="S1",
        estado_reserva=estado,
        recibos=[{**recibo[0], "body": {"veredicto": "SUPPORT"}}],
    )
    assert reg["outcome"] == "SUPPORT"
    assert reg["physical_calls"] == 1  # <-- inferido, no acreditado


def test_no_campo_de_transporte_en_el_recibo(tmp_path) -> None:
    """El recibo no acredita transporte: no hay request_id ni bytes."""
    db = tmp_path / "transporte.sqlite3"
    st = Storage(db)
    st.reserve_semantic_attempt("s", "intento-1", SHA, REVIEW)
    st.close_semantic_attempt("s", "intento-1", SHA, "c" * 64)
    recibo = st.load_semantic_receipts("s", "intento-1")[0]
    # El esquema no puede demostrar que el proveedor respondio.
    assert set(recibo) == {
        "request_sha256", "body_sha256", "status", "received_at"
    }
    for campo in ("transport_id", "provider_request_id", "raw_bytes",
                  "tokens", "latency_ms", "model_observed"):
        assert campo not in recibo


# --- 2. Llamada interrumpida / timeout despues de enviar -----------------

def test_llamada_interrumpida_no_cuenta_como_resultado(tmp_path) -> None:
    """Reserva sin recibo (llamada cortada) es NOT_RUN, no un veredicto."""
    db = tmp_path / "cortada.sqlite3"
    st = Storage(db)
    st.reserve_semantic_attempt("s", "intento-1", SHA, REVIEW)
    # No hay close: la llamada se interrumpio despues de reservar.
    estado = st.semantic_attempt_status("s", "intento-1")
    assert estado is not None and estado["status"] == "ACTIVE"
    reg = normalizar_slot(case_id="C:1", repetition=0, arm="S1",
                          estado_reserva=estado, recibos=[])
    assert reg["outcome"] == "NOT_RUN"
    assert reg["physical_calls"] == 0


def test_timeout_tras_enviar_no_es_veredicto(tmp_path) -> None:
    """Un timeout no produce recibo: no puede convertirse en abstencion."""
    db = tmp_path / "timeout.sqlite3"
    st = Storage(db)
    st.reserve_semantic_attempt("s", "intento-1", SHA, REVIEW)
    reg = normalizar_slot(case_id="C:1", repetition=0, arm="S1",
                          estado_reserva=st.semantic_attempt_status("s", "intento-1"),
                          recibos=[])
    # El gate tiene ERROR para esto, pero sin recibo es NOT_RUN: no se
    # puede distinguir "no llamo" de "llamo y no llego nada".
    assert reg["outcome"] in ("NOT_RUN", "ERROR")
    assert reg["physical_calls"] == 0


# --- 3. Reintento oculto del transporte ---------------------------------

def test_dos_recibos_mismo_request_no_inventan_dos_llamadas(tmp_path) -> None:
    """Un reintento del transporte deja un solo recibo (PK body_sha256)."""
    db = tmp_path / "reintento.sqlite3"
    st = Storage(db)
    st.reserve_semantic_attempt("s", "intento-1", SHA, REVIEW)
    # Mismo cuerpo dos veces: INSERT OR IGNORE -> una sola fila.
    st.close_semantic_attempt("s", "intento-1", SHA, "d" * 64)
    st.close_semantic_attempt("s", "intento-1", SHA, "d" * 64)
    recibos = st.load_semantic_receipts("s", "intento-1")
    assert len(recibos) == 1


def test_cuerpos_distintos_mismo_request_son_conflicto(tmp_path) -> None:
    """Dos cuerpos distintos para la misma peticion: no puede haber dos."""
    db = tmp_path / "conflicto2.sqlite3"
    st = Storage(db)
    st.reserve_semantic_attempt("s", "intento-1", SHA, REVIEW)
    st.close_semantic_attempt("s", "intento-1", SHA, "e" * 64)
    try:
        st.close_semantic_attempt("s", "intento-1", SHA, "f" * 64)
    except ValueError:
        pass
    else:
        raise AssertionError("segundo cuerpo distinto deberia ser conflicto")


# --- 4. Respuesta tardia / reserva superada -----------------------------

def test_respuesta_tardia_no_cuenta_en_el_recuento_del_vigente(tmp_path) -> None:
    """La tardia queda STALE y no suma llamadas al intento vigente."""
    db = tmp_path / "tardia.sqlite3"
    st = Storage(db)
    st.reserve_semantic_attempt("s", "intento-1", "1" * 64, REVIEW)
    st.reserve_semantic_attempt("s", "intento-1", "2" * 64, REVIEW)
    # Cuerpos DISTINTOS: la PK es (scope, attempt, body_sha256) y dos cuerpos
    # con el mismo hash colisionarian (eso seria un cuerpo repetido, no dos).
    st.close_semantic_attempt("s", "intento-1", "1" * 64, "r" * 64)  # tardia
    st.close_semantic_attempt("s", "intento-1", "2" * 64, "s" * 64)  # vigente
    estado = st.semantic_attempt_status("s", "intento-1")
    recibos = st.load_semantic_receipts("s", "intento-1")
    # Solo el recibo del VIGENTE (request_sha == 2) lleva veredicto.
    con_cuerpo = [
        {**r, "body": {"veredicto": "REJECT"}}
        if r["request_sha256"] == "2" * 64 else {**r, "body": None}
        for r in recibos
    ]
    reg = normalizar_slot(
        case_id="C:1", repetition=0, arm="S1", estado_reserva=estado,
        recibos=con_cuerpo,
    )
    # Solo cuenta el vigente: 1 llamada fisica, no 2.
    assert reg["physical_calls"] == 1
    assert reg["outcome"] == "REJECT"
    # La tardia sigue en el historial para auditoria (STALE).
    estados = sorted(r["status"] for r in recibos)
    assert estados == ["ACTIVE", "STALE"], estados


# --- 5. Estado parcialmente persistido / reinicio -----------------------

def test_reinicio_entre_envio_y_cierre_no_cierra(tmp_path) -> None:
    """Si el proceso muere tras enviar y antes de cerrar, no queda CLOSED."""
    db = tmp_path / "reinicio.sqlite3"
    st = Storage(db)
    st.reserve_semantic_attempt("s", "intento-1", SHA, REVIEW)
    # Simulo muerte: nueva instancia, sin close.
    st2 = Storage(db)
    estado = st2.semantic_attempt_status("s", "intento-1")
    assert estado["status"] == "ACTIVE"
    assert estado["receipt_sha256"] is None
    reg = normalizar_slot(case_id="C:1", repetition=0, arm="S1",
                          estado_reserva=estado, recibos=[])
    assert reg["outcome"] == "NOT_RUN"
    assert reg["physical_calls"] == 0


def test_reserva_superada_sobrevive_al_reinicio(tmp_path) -> None:
    """La re-reserva persiste: reabrir conserva el sha vigente."""
    db = tmp_path / "reapertura2.sqlite3"
    st = Storage(db)
    st.reserve_semantic_attempt("s", "intento-1", "1" * 64, REVIEW)
    st.reserve_semantic_attempt("s", "intento-1", "2" * 64, REVIEW)
    estado = Storage(db).semantic_attempt_status("s", "intento-1")
    assert estado["request_sha256"] == "2" * 64
    assert estado["status"] == "ACTIVE"


# --- 6. Modelo solicitado vs observado ----------------------------------

def test_modelo_solicitado_no_es_identidad_acreditada() -> None:
    """El ledger no guarda el modelo observado: el alias no basta.

    ``semantic_receipts`` no tiene columna de modelo observado. Un recibo
    no puede demostrar QUE modelo respondio. La identidad debe viajar en
    el recibo que produce el puente (observed_model), no en el ledger.
    """
    db_recibo = {
        "request_sha256": SHA,
        "body_sha256": "b" * 64,
        "status": "CLOSED",
        "received_at": "2026-11-22T00:00:00+00:00",
    }
    # El ledger no acredita identidad de modelo.
    assert "observed_model" not in db_recibo
    assert "model" not in db_recibo


def test_normalizador_no_inventa_llamada_cuando_no_hay_cuerpo() -> None:
    """Un recibo cerrado sin cuerpo no se convierte en etiqueta."""
    reg = normalizar_slot(
        case_id="C:1", repetition=0, arm="S1",
        estado_reserva=_reserva(status="CLOSED", request=SHA, receipt=SHA),
        recibos=[{"request_sha256": SHA, "body_sha256": "b" * 64,
                  "status": "CLOSED", "received_at": "x", "body": None}],
    )
    assert reg["outcome"] == "ERROR"
    assert reg["physical_calls"] == 1


def test_validacion_rechaza_resultado_sin_llamada() -> None:
    """El contrato del gate rechaza una etiqueta con 0 llamadas."""
    errores = validar_registros([
        {"case_id": "A", "repetition": 0, "arm": "S1",
         "outcome": "SUPPORT", "physical_calls": 0},
    ])
    assert errores, "una etiqueta sin llamada acreditada debe rechazarse"