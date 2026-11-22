"""Reproduccion de carrera en rutas read-modify-write del Storage.

No modifica produccion: solo DEMUESTRA si la ruta pierde escrituras
cuando dos hilos entran a la vez. Se ejecuta contra la version actual
para decidir si hace falta reparar.

Cada prueba usa una barrera (Event) para forzar el interleave, no sleeps.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event

from criba.storage import Storage


def _seed(store: Storage, ident: str = "s") -> None:
    con = store.connect()
    try:
        with con:
            con.execute(
                "INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
                (ident, "2026-09-21T00:00:00+00:00", "h", "query", "c",
                 "ACTIVATED", "{}", "{}", "[]"),
            )
    finally:
        con.close()


def test_save_chain_memory_no_pierde_campos(tmp_path) -> None:
    """Dos hilos guardan el MISMO campo con valores distintos.

    Read-modify-write sin lock: ambos pueden leer "no existe" y ambos
    insertar; o uno puede leer y el otro insertar entremedias. El
    invariante minimo es que el segundo valor no se pierda en silencio.
    """
    db = tmp_path / "chain-memory.sqlite3"
    store = Storage(db)
    store.save_chain_session("cadena", "objetivo", 0, "ACTIVE")
    barrera = Event()
    resultados: list[str] = []

    def guardar(valor: str) -> None:
        barrera.wait(10)
        store.save_chain_memory("cadena", 1, {"campo": valor})
        resultados.append(valor)

    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(guardar, "A"), ex.submit(guardar, "B")]
        for f in futs:
            f.result(timeout=30)
    barrera.set()

    con = store.connect()
    try:
        filas = con.execute(
            "SELECT field_value FROM chain_memory WHERE chain_id=? AND stage=? "
            "AND field_name=?",
            ("cadena", 1, "campo"),
        ).fetchall()
    finally:
        con.close()
    valores = sorted(str(f[0]) for f in filas)
    # Con el lock, ambos valores sobreviven; sin el, uno se pierde.
    assert valores == ["A", "B"], f"valores persistidos: {valores}"


def test_save_chain_memory_no_duplica_campos(tmp_path) -> None:
    """Dos hilos guardan el MISMO campo con el MISMO valor: sin duplicados."""
    db = tmp_path / "chain-memory-dup.sqlite3"
    store = Storage(db)
    store.save_chain_session("cadena", "objetivo", 0, "ACTIVE")
    barrera = Event()

    def guardar() -> None:
        barrera.wait(10)
        store.save_chain_memory("cadena", 2, {"campo": "valor"})

    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(guardar) for _ in range(2)]
        for f in futs:
            f.result(timeout=30)
    barrera.set()

    con = store.connect()
    try:
        n = con.execute(
            "SELECT COUNT(*) FROM chain_memory WHERE chain_id=? AND stage=? "
            "AND field_name=?",
            ("cadena", 2, "campo"),
        ).fetchone()[0]
    finally:
        con.close()
    assert n == 1, f"duplicados: {n}"


def test_guardar_decision_y_evento_no_se_pisan(tmp_path) -> None:
    """Decision y evento concurrentes: ambos deben sobrevivir."""
    db = tmp_path / "mix.sqlite3"
    store = Storage(db)
    _seed(store)
    barrera = Event()
    ids: dict[str, str] = {}

    def decision() -> None:
        barrera.wait(10)
        ids["decision"] = store.record_decision(
            "s", "ADOPTAR", {"via": "decision"})["id"]

    def evento() -> None:
        barrera.wait(10)
        ids["evento"] = store.record_event(
            "s", "mitigation_proposed", {"via": "evento"})["id"]

    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(decision), ex.submit(evento)]
        for f in futs:
            f.result(timeout=30)
    barrera.set()

    evidencia = store.get("s")["evidence"]
    assert len(evidencia) == 2, f"evidencia perdida: {len(evidencia)}"
    assert {e["id"] for e in evidencia} == set(ids.values())