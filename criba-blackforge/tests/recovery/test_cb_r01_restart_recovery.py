"""CB-R01: recuperación tras reinicio real — almacenamiento local de CRIBA.

Complementa CB-I03 (SUPRA) y CB-03 (journey con proceso). Aquí se prueba la ruta
de almacenamiento LOCAL de CRIBA que Shadow usa para reabrir trabajo tras cerrar:
guardar_dossier → cargar_dossier → cargar_ultimo_dossier, contra disco real.

Invariantes verificados (del megaprompt):
- disco es fuente de verdad: lo guardado se recupera íntegro
- lineage preservado: identidad y contenido sobreviven el reinicio
- incompleto se muestra incompleto: un protocolo no discriminante no se disfraza
- sin fabricar resultados: no se inventa lo que no se guardó
- PERSISTED != EXECUTED

Sin proceso: la "persistencia" se simula cerrando y reabriendo el módulo de
lectura sobre el mismo directorio (directory aislado bajo tmp_path).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from criba.supra_dossier import (
    _discriminant_protocol_complete,
    cargar_dossier,
    cargar_ultimo_dossier,
    guardar_dossier,
    preparar_dossier,
)


def _entry() -> dict:
    return {
        "candidate_id": "idea-r01",
        "claim_id": "",
        "hipotesis": "La confirmación automática reduce segundas visitas.",
        "mecanismo": (
            "El sistema detecta el registro incompleto al momento de la entrada "
            "(variable intermedia: detección temprana), bloquea su propagación al "
            "registro oficial (variable intermedia: error bloqueado), y reduce la "
            "necesidad de corrección posterior (efecto observable: menos visitas)."
        ),
        "prueba_concreta": "Ensayo controlado midiendo segundas visitas por registro incompleto.",
        "supuestos": ["Los usuarios corrigen errores cuando se les notifica."],
        "observable": "número de segundas visitas por registro incompleto",
        "prueba": {
            "metrica": "Número de segundas visitas por registro incompleto",
            "baseline": "Sin confirmación automática",
            "umbral": "20% de reducción",
            "condicion_fracaso": "No se observa reducción significativa",
            "alternativa_explicativa": "Mejora en comunicación entre profesionales",
            "resultado_favorable_mecanismo": "Se reduce 20% las segundas visitas",
            "resultado_favorable_alternativa": "No se reduce las segundas visitas",
        },
    }


def _dossier_valido(problema: str = "Eliminar segundas visitas por errores de registro.") -> dict:
    return preparar_dossier(_entry(), problema, ficha_bloqueo={"title": "salud"})


# --------------------------------------------------------------------------
# Ciclo: guardar → recuperar por identidad
# --------------------------------------------------------------------------


def test_guardar_y_recuperar_por_identidad(tmp_path: Path) -> None:
    """Un dossier guardado se recupera íntegro por su dossier_id (lineage)."""
    dossier = _dossier_valido()
    guardar_dossier(dossier, tmp_path)

    recuperado = cargar_dossier(dossier["dossier_id"], tmp_path)
    assert recuperado is not None
    assert recuperado["dossier_id"] == dossier["dossier_id"]
    assert recuperado["hipotesis"] == dossier["hipotesis"]
    assert recuperado["mecanismo"] == dossier["mecanismo"]
    # El protocolo discriminante sobrevive intacto.
    assert recuperado["prueba_discriminante"] == dossier["prueba_discriminante"]


def test_reinicio_carga_ultimo_por_defecto(tmp_path: Path) -> None:
    """Tras reinicio (sin identidad), cargar_ultimo_dossier devuelve el más reciente."""
    d1 = _dossier_valido("Problema uno")
    d2 = _dossier_valido("Problema dos")
    guardar_dossier(d1, tmp_path)
    guardar_dossier(d2, tmp_path)

    ultimo = cargar_ultimo_dossier(tmp_path)
    assert ultimo is not None
    # El último guardado es el recuperado.
    assert ultimo["dossier_id"] == d2["dossier_id"]
    assert ultimo["problema"] == "Problema dos"


def test_multiples_dossiers_sobreviven_reinicio(tmp_path: Path) -> None:
    """Todo el historial guardado sigue siendo recuperable tras reinicio."""
    ids = []
    for i in range(3):
        d = _dossier_valido(f"Problema persistente {i}")
        guardar_dossier(d, tmp_path)
        ids.append(d["dossier_id"])

    for did in ids:
        assert cargar_dossier(did, tmp_path) is not None


# --------------------------------------------------------------------------
# Identidad inexistente / recuperación honesta
# --------------------------------------------------------------------------


def test_identidad_inexistente_devuelve_none(tmp_path: Path) -> None:
    """Pedir un dossier que no existe devuelve None, no uno fabricado."""
    assert cargar_dossier("dossier-que-no-existe", tmp_path) is None


def test_directorio_vacio_devuelve_none(tmp_path: Path) -> None:
    """Sin dossiers guardados, no hay último que recuperar."""
    assert cargar_ultimo_dossier(tmp_path) is None


# --------------------------------------------------------------------------
# Incompleto se muestra incompleto
# --------------------------------------------------------------------------


def test_protocolo_no_discriminante_no_se_disfraza(tmp_path: Path) -> None:
    """Un dossier sin protocolo completo se marca como no discriminante, no se completa solo."""
    dossier = _dossier_valido()
    # Vaciamos un campo obligatorio del protocolo.
    dossier["prueba_discriminante"]["observable"] = ""
    guardar_dossier(dossier, tmp_path)

    recuperado = cargar_dossier(dossier["dossier_id"], tmp_path)
    assert recuperado is not None
    assert not _discriminant_protocol_complete(recuperado)
    # No se rellenó automáticamente: sigue vacío.
    assert recuperado["prueba_discriminante"]["observable"] == ""


def test_dossier_completo_es_discriminante(tmp_path: Path) -> None:
    """El dossier completo sí es discriminante (control del test anterior)."""
    dossier = _dossier_valido()
    guardar_dossier(dossier, tmp_path)
    recuperado = cargar_dossier(dossier["dossier_id"], tmp_path)
    assert recuperado is not None
    assert _discriminant_protocol_complete(recuperado)


# --------------------------------------------------------------------------
# Escritura parcial / historial corrupto: recuperación resiliente
# --------------------------------------------------------------------------


def test_linea_corrupta_no_impide_recuperar_las_validas(tmp_path: Path) -> None:
    """Una línea corrupta en el JSONL no borra ni oculta los dossiers válidos."""
    d = _dossier_valido()
    guardar_dossier(d, tmp_path)
    # Añadimos una línea basura al final del historial.
    path = tmp_path / "dossiers.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("esta linea no es json valido\n")

    # El dossier válido sigue recuperable pese a la línea corrupta.
    recuperado = cargar_dossier(d["dossier_id"], tmp_path)
    assert recuperado is not None
    assert recuperado["hipotesis"] == d["hipotesis"]


def test_identidad_vacia_es_rechazada(tmp_path: Path) -> None:
    """Guardar sin dossier_id es un error explícito, no un registro anónimo."""
    dossier = _dossier_valido()
    dossier["dossier_id"] = ""
    with pytest.raises(ValueError, match="dossier_id"):
        guardar_dossier(dossier, tmp_path)


def test_mismo_contenido_es_idempotente(tmp_path: Path) -> None:
    """Re-guardar el mismo dossier (mismo contexto) no duplica ni corrompe."""
    dossier = _dossier_valido()
    guardar_dossier(dossier, tmp_path)
    guardar_dossier(dossier, tmp_path)  # segunda vez, mismo contenido

    recuperado = cargar_dossier(dossier["dossier_id"], tmp_path)
    assert recuperado is not None
    # Una sola entrada recuperable, idéntica.
    lineas = (tmp_path / "dossiers.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas) == 1


# --------------------------------------------------------------------------
# PERSISTED != EXECUTED
# --------------------------------------------------------------------------


def test_dossier_guardado_no_es_resultado_ejecutado(tmp_path: Path) -> None:
    """Guardar un dossier lo deja en estado pendiente de ejecución, no ejecutado."""
    dossier = _dossier_valido()
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    guardar_dossier(dossier, tmp_path)

    recuperado = cargar_dossier(dossier["dossier_id"], tmp_path)
    assert recuperado is not None
    assert recuperado["estado"] == "SUPRA_EJECUCION_PENDIENTE"
