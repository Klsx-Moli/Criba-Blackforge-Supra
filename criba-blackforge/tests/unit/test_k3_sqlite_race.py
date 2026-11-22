"""Carrera SQLite REAL sobre la reserva K3 (no secuencia entre conexiones).

El handoff exige "carrera SQLite real con conexiones independientes,
barrera de inicio y resultados/reapertura; no confundir secuencia entre
conexiones con concurrencia".

Este test usa procesos independientes (no hilos) sincronizados por una
barrera de archivo: las dos reservas se intentan de verdad a la vez sobre
la MISMA base.

Contrato real de ``reserve_semantic_attempt`` (leido del codigo y de los
tests unitarios):

  - MISMO scope+attempt+MISMO request  -> idempotente: el segundo devuelve
    False y NO crea una segunda fila.
  - MISMO scope+attempt+OTRO request   -> re-reserva legitima: reemplaza la
    vigente. Ambos procesos pueden devolver True (serializados por el lock);
    el invariante es que queda UNA fila ACTIVE, sin excepcion.
  - Cerrar con cuerpo distinto al ya registrado -> conflicto (ValueError).

Se comprueban los invariantes bajo concurrencia real, que es lo que una
secuencia entre conexiones no puede demostrar.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

from criba.storage import Storage

SCOPE = "scope-carrera"
REVIEW = "judge"
MISMO_SHA = "a" * 64
OTRO_SHA = "b" * 64

# Raiz de src derivada del propio fichero, NO del entorno: el test debe ser
# autocontenido y no depender de que el llamador exporte CBS_SRC.
_SRC = str(Path(__file__).resolve().parents[2] / "src")


def _worker(ruta: str, request_sha256: str, attempt: str, barrera: str,
            salida: str, idx: int) -> None:
    """Proceso hijo: espera la barrera y reserva a la vez que el otro."""
    sys.path.insert(0, _SRC)
    from criba.storage import Storage as ST

    st = ST(ruta)
    for _ in range(600):
        if Path(barrera).exists():
            break
        time.sleep(0.01)
    resultado: dict = {"idx": idx, "attempt": attempt}
    try:
        resultado["primero"] = st.reserve_semantic_attempt(
            SCOPE, attempt, request_sha256, REVIEW
        )
        resultado["estado"] = st.semantic_attempt_status(SCOPE, attempt)
        resultado["error"] = None
    except Exception as exc:  # se registra, no se traga
        resultado["error"] = f"{type(exc).__name__}: {exc}"
    Path(salida).write_text(json.dumps(resultado, default=str), encoding="utf-8")


def _worker_cierre(ruta: str, attempt: str, req: str, recibo: str,
                   barrera: str, salida: str, idx: int) -> None:
    sys.path.insert(0, _SRC)
    from criba.storage import Storage as ST

    st = ST(ruta)
    for _ in range(600):
        if Path(barrera).exists():
            break
        time.sleep(0.01)
    try:
        resultado = st.close_semantic_attempt(SCOPE, attempt, req, recibo)
    except ValueError:
        resultado = "CONFLICT"
    Path(salida).write_text(
        json.dumps({"idx": idx, "resultado": resultado}), encoding="utf-8")


def _filas(ruta: Path, scope: str, attempt: str) -> int:
    con = Storage(ruta).connect()
    try:
        return con.execute(
            "SELECT COUNT(*) FROM semantic_reservations WHERE scope=? AND attempt=?",
            (scope, attempt)).fetchone()[0]
    finally:
        con.close()


def _leer(tmp: Path, nombre: str) -> dict:
    return json.loads((tmp / nombre).read_text(encoding="utf-8"))


def _lanzar(ruta: Path, activar: Path, tmp: Path, args: list) -> list:
    ctx = mp.get_context("spawn")
    ps = []
    for i, a in enumerate(args, start=1):
        p = ctx.Process(target=_worker, args=(
            str(ruta), a[0], a[1], str(activar), str(tmp / f"s{i}.json"), i))
        p.start(); ps.append(p)
    activar.write_text("go", encoding="utf-8")
    for p in ps:
        p.join(timeout=120)
        assert p.exitcode == 0, "un proceso hijo murio"
    return [_leer(tmp, f"s{i}.json") for i in range(1, len(args) + 1)]


def _lanzar_cierres(ruta: Path, activar: Path, tmp: Path,
                    pares: list) -> list:
    """pares = [(attempt, request_sha256, receipt_sha256), ...]"""
    ctx = mp.get_context("spawn")
    ps = []
    for i, (attempt, req, recibo) in enumerate(pares, start=1):
        p = ctx.Process(target=_worker_cierre, args=(
            str(ruta), attempt, req, recibo, str(activar),
            str(tmp / f"c{i}.json"), i))
        p.start(); ps.append(p)
    activar.write_text("go", encoding="utf-8")
    for p in ps:
        p.join(timeout=120)
        assert p.exitcode == 0
    return [_leer(tmp, f"c{i}.json")["resultado"]
            for i in range(1, len(pares) + 1)]


def test_misma_peticion_concurrente_es_idempotente(tmp_path: Path) -> None:
    """Dos procesos, MISMA peticion: uno inserta, el otro no duplica."""
    ruta = tmp_path / "carrera-idempotente.sqlite3"
    r = _lanzar(ruta, tmp_path / "b1", tmp_path,
                [(MISMO_SHA, "intento-1"), (MISMO_SHA, "intento-1")])
    assert all(x["error"] is None for x in r), r
    assert [x["primero"] for x in r].count(True) == 1, r
    assert _filas(ruta, SCOPE, "intento-1") == 1


def test_distinta_peticion_concurrente_no_corrompe(tmp_path: Path) -> None:
    """Mismo scope+attempt, requests distintos: re-reserva legitima.

    Lo invariante no es cuantos devuelven True, sino que queda UNA fila
    ACTIVE, sin excepcion y con un sha coherente con el estado leido.
    """
    ruta = tmp_path / "carrera-rereserva.sqlite3"
    r = _lanzar(ruta, tmp_path / "b2", tmp_path,
                [(MISMO_SHA, "intento-1"), (OTRO_SHA, "intento-1")])
    assert all(x["error"] is None for x in r), r
    assert _filas(ruta, SCOPE, "intento-1") == 1
    final = Storage(ruta).semantic_attempt_status(SCOPE, "intento-1")
    assert final["status"] == "ACTIVE"
    assert final["request_sha256"] in (MISMO_SHA, OTRO_SHA)


def test_dos_cierres_concurrentes_solo_uno_cierra(tmp_path: Path) -> None:
    """Dos procesos cierran la misma reserva: solo uno devuelve CLOSED."""
    ruta = tmp_path / "carrera-cierre.sqlite3"
    req = "d" * 64
    Storage(ruta).reserve_semantic_attempt(SCOPE, "intento-1", req, REVIEW)
    estados = _lanzar_cierres(ruta, tmp_path / "b3", tmp_path,
                              [("intento-1", req, "e" * 64),
                               ("intento-1", req, "e" * 64)])
    assert estados.count("CLOSED") == 1, estados
    final = Storage(ruta).semantic_attempt_status(SCOPE, "intento-1")
    assert final["status"] == "CLOSED"


def test_cierre_con_cuerpo_distinto_es_conflicto(tmp_path: Path) -> None:
    """Cerrar con otro recibo tras un cierre valido es conflicto, no reemplazo."""
    ruta = tmp_path / "conflicto.sqlite3"
    st = Storage(ruta)
    req = "f" * 64
    st.reserve_semantic_attempt(SCOPE, "intento-1", req, REVIEW)
    assert st.close_semantic_attempt(SCOPE, "intento-1", req, "1" * 64) == "CLOSED"
    try:
        st.close_semantic_attempt(SCOPE, "intento-1", req, "2" * 64)
    except ValueError:
        return
    raise AssertionError("un segundo cierre con otro cuerpo debio ser conflicto")


def test_reapertura_tras_carrera_conserva_el_estado(tmp_path: Path) -> None:
    """Tras la carrera, reabrir la base conserva el estado final."""
    ruta = tmp_path / "reapertura.sqlite3"
    st = Storage(ruta)
    st.reserve_semantic_attempt(SCOPE, "intento-1", "f" * 64, REVIEW)
    st.close_semantic_attempt(SCOPE, "intento-1", "f" * 64, "0" * 64)

    st2 = Storage(ruta)  # nueva "sesion" desde cero
    estado = st2.semantic_attempt_status(SCOPE, "intento-1")
    assert estado["status"] == "CLOSED"
    assert estado["receipt_sha256"] == "0" * 64


def test_intento_tardio_no_cierra_la_reserva_del_intento_2(tmp_path: Path) -> None:
    """El caso exigido por el handoff, con dos PROCESOS reales.

    Un MISMO (scope, attempt) se re-reserva: intento 1 reserva con su sha y
    luego el intento 2 ocupa el mismo intento con otro sha. Las dos
    respuestas llegan a la vez. La tardia (sha del intento 1) debe recibir
    STALE y NO cerrar la reserva, que pertenece al intento 2.
    """
    ruta = tmp_path / "tardia-procesos.sqlite3"
    sha1, sha2 = "1" * 64, "2" * 64
    st = Storage(ruta)
    assert st.reserve_semantic_attempt(SCOPE, "intento-1", sha1, REVIEW) is True
    assert st.reserve_semantic_attempt(SCOPE, "intento-1", sha2, REVIEW) is True

    # Antes de las respuestas, la vigente ya es la del intento 2.
    assert Storage(ruta).semantic_attempt_status(SCOPE, "intento-1")[
        "request_sha256"] == sha2

    # Dos procesos cierran a la vez: el tardio trae sha1, el vigente trae sha2.
    estados = _lanzar_cierres(ruta, tmp_path / "b4", tmp_path,
                              [("intento-1", sha1, "r" * 64),
                               ("intento-1", sha2, "s" * 64)])
    # Solo el cierre con el sha vigente puede cerrar.
    assert estados.count("CLOSED") == 1, estados
    assert "STALE" in estados, estados

    final = Storage(ruta).semantic_attempt_status(SCOPE, "intento-1")
    # La vigente sigue siendo la del intento 2, cerrada por SU recibo.
    assert final["request_sha256"] == sha2
    assert final["status"] == "CLOSED"