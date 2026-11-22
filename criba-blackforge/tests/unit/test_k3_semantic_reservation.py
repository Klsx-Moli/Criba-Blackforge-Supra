"""K3 - Reserva de intento y cierre condicional en el ledger recuperable.

Caso central exigido: un intento 1 que llega TARDE, despues de que el
intento 2 ya reservo, NO puede cerrar la reserva del intento 2.

Se demuestra con dos conexiones y reabertura de base, para no confundir
un test puro con una prueba de carrera SQLite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from criba.storage import Storage

SCOPE = "scope-prueba-k3"
REQUEST_1 = "a" * 64
REQUEST_2 = "b" * 64
RECEIPT_1 = "1" * 64
RECEIPT_2 = "2" * 64


def _storage(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "k3.sqlite3")


def test_reserva_nueva_devuelve_true_y_repetida_false(tmp_path: Path) -> None:
    st = _storage(tmp_path)
    assert st.reserve_semantic_attempt(SCOPE, "intento-1", REQUEST_1, "judge") is True
    assert st.reserve_semantic_attempt(SCOPE, "intento-1", REQUEST_1, "judge") is False


def test_reserva_conflictiva_con_otro_request_es_reintento(tmp_path: Path) -> None:
    """Otro request para el mismo intento es un REINTENTO, no un error.

    Antes de K3 esto se rechazaba. Ahora se acepta y sustituye, porque es
    justo lo que permite que una respuesta tardia no cierre lo vigente.
    """
    st = _storage(tmp_path)
    st.reserve_semantic_attempt(SCOPE, "intento-1", REQUEST_1, "judge")
    assert st.reserve_semantic_attempt(
        SCOPE, "intento-1", REQUEST_2, "judge"
    ) is True
    estado = st.semantic_attempt_status(SCOPE, "intento-1")
    assert estado is not None and estado["request_sha256"] == REQUEST_2


def test_cierre_normal_marca_closed(tmp_path: Path) -> None:
    st = _storage(tmp_path)
    st.reserve_semantic_attempt(SCOPE, "intento-1", REQUEST_1, "judge")
    assert st.close_semantic_attempt(
        SCOPE, "intento-1", REQUEST_1, RECEIPT_1
    ) == "CLOSED"
    estado = st.semantic_attempt_status(SCOPE, "intento-1")
    assert estado is not None and estado["status"] == "CLOSED"
    assert estado["receipt_sha256"] == RECEIPT_1


def test_cierre_repetido_identico_no_duplica(tmp_path: Path) -> None:
    st = _storage(tmp_path)
    st.reserve_semantic_attempt(SCOPE, "intento-1", REQUEST_1, "judge")
    assert st.close_semantic_attempt(SCOPE, "intento-1", REQUEST_1, RECEIPT_1) == "CLOSED"
    assert st.close_semantic_attempt(
        SCOPE, "intento-1", REQUEST_1, RECEIPT_1
    ) == "ALREADY_CLOSED"
    recibos = st.load_semantic_receipts(SCOPE, "intento-1")
    assert len(recibos) == 1


def test_mismo_intento_distinto_cuerpo_es_conflicto(tmp_path: Path) -> None:
    st = _storage(tmp_path)
    st.reserve_semantic_attempt(SCOPE, "intento-1", REQUEST_1, "judge")
    st.close_semantic_attempt(SCOPE, "intento-1", REQUEST_1, RECEIPT_1)
    with pytest.raises(ValueError):
        st.close_semantic_attempt(SCOPE, "intento-1", REQUEST_1, RECEIPT_2)


def test_intento_tardio_no_cierra_la_reserva_del_intento_2(tmp_path: Path) -> None:
    """El caso exigido: intento 1 llega tarde tras reservar el intento 2.

    Un scope tiene UN intento activo. El intento 1 se reserva y queda
    colgado; el intento 2 RE-RESERVA el mismo intento con otro request.
    Cuando llega la respuesta tardia del intento 1, no cierra nada vigente.
    """
    st = _storage(tmp_path)
    # Intento 1: peticion original, sin respuesta.
    assert st.reserve_semantic_attempt(
        SCOPE, "intento-1", REQUEST_1, "judge"
    ) is True
    # Intento 2: reintento con otra peticion. Sustituye a la anterior.
    assert st.reserve_semantic_attempt(
        SCOPE, "intento-1", REQUEST_2, "judge"
    ) is True

    # La reserva vigente es ahora la del intento 2.
    estado = st.semantic_attempt_status(SCOPE, "intento-1")
    assert estado is not None
    assert estado["status"] == "ACTIVE"
    assert estado["request_sha256"] == REQUEST_2
    assert estado["receipt_sha256"] is None

    # Llega MUY tarde la respuesta del intento 1: NO cierra lo vigente.
    assert st.close_semantic_attempt(
        SCOPE, "intento-1", REQUEST_1, RECEIPT_1
    ) == "STALE"

    # La reserva del intento 2 sigue intacta y abierta.
    estado = st.semantic_attempt_status(SCOPE, "intento-1")
    assert estado is not None and estado["status"] == "ACTIVE"
    assert estado["receipt_sha256"] is None

    # El recibo tardio queda guardado para auditoria, pero marcado STALE.
    recibos = st.load_semantic_receipts(SCOPE, "intento-1")
    assert len(recibos) == 1
    assert recibos[0]["status"] == "STALE"
    assert recibos[0]["request_sha256"] == REQUEST_1

    # El intento 2 SI puede cerrarse con su propio recibo.
    assert st.close_semantic_attempt(
        SCOPE, "intento-1", REQUEST_2, RECEIPT_2
    ) == "CLOSED"
    estado = st.semantic_attempt_status(SCOPE, "intento-1")
    assert estado is not None and estado["status"] == "CLOSED"


def test_reintento_supera_la_reserva_anterior(tmp_path: Path) -> None:
    """La re-reserva marca SUPERSEDED la peticion anterior antes de sustituirla."""
    st = _storage(tmp_path)
    st.reserve_semantic_attempt(SCOPE, "intento-1", REQUEST_1, "judge")
    st.reserve_semantic_attempt(SCOPE, "intento-1", REQUEST_2, "judge")
    # Solo hay una fila vigente: la del intento 2.
    estado = st.semantic_attempt_status(SCOPE, "intento-1")
    assert estado is not None and estado["request_sha256"] == REQUEST_2


def test_reserva_repetida_identica_no_es_nueva(tmp_path: Path) -> None:
    """Repetir la MISMA peticion no crea reserva nueva ni pierde vigencia."""
    st = _storage(tmp_path)
    assert st.reserve_semantic_attempt(
        SCOPE, "intento-1", REQUEST_1, "judge"
    ) is True
    assert st.reserve_semantic_attempt(
        SCOPE, "intento-1", REQUEST_1, "judge"
    ) is False
    # Sigue activa y con el mismo request.
    estado = st.semantic_attempt_status(SCOPE, "intento-1")
    assert estado is not None and estado["request_sha256"] == REQUEST_1


def test_reserva_desconocida_no_es_exito(tmp_path: Path) -> None:
    st = _storage(tmp_path)
    assert st.close_semantic_attempt(
        SCOPE, "no-existe", REQUEST_1, RECEIPT_1
    ) == "UNKNOWN"
    assert st.semantic_attempt_status(SCOPE, "no-existe") is None


def test_persistencia_entre_conexiones_y_reapertura(tmp_path: Path) -> None:
    """Dos conexiones y reabrir la base conservan la reserva y el cierre."""
    ruta = tmp_path / "persistente.sqlite3"
    st1 = Storage(ruta)
    st1.reserve_semantic_attempt(SCOPE, "intento-1", REQUEST_1, "judge")

    # Segunda conexion: otra instancia sobre la misma base ve la reserva.
    st2 = Storage(ruta)
    estado = st2.semantic_attempt_status(SCOPE, "intento-1")
    assert estado is not None and estado["status"] == "ACTIVE"

    # El cierre desde una conexion se ve desde la otra.
    assert st2.close_semantic_attempt(
        SCOPE, "intento-1", REQUEST_1, RECEIPT_1
    ) == "CLOSED"

    # Reabrir la base desde cero conserva el estado cerrado.
    st3 = Storage(ruta)
    estado = st3.semantic_attempt_status(SCOPE, "intento-1")
    assert estado is not None and estado["status"] == "CLOSED"
    assert estado["receipt_sha256"] == RECEIPT_1


def test_reserva_tardia_no_afecta_a_otra_conexion(tmp_path: Path) -> None:
    """La re-reserva del intento 2, leida desde otra conexion, sigue activa."""
    ruta = tmp_path / "concurrente.sqlite3"
    st1 = Storage(ruta)
    st1.reserve_semantic_attempt(SCOPE, "intento-1", REQUEST_1, "judge")
    st1.reserve_semantic_attempt(SCOPE, "intento-1", REQUEST_2, "judge")

    st2 = Storage(ruta)
    assert st2.close_semantic_attempt(
        SCOPE, "intento-1", REQUEST_1, RECEIPT_1
    ) == "STALE"

    estado = st2.semantic_attempt_status(SCOPE, "intento-1")
    assert estado is not None and estado["status"] == "ACTIVE"
    assert estado["request_sha256"] == REQUEST_2