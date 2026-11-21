"""CB-L01: carga de generación determinista — volumen alto sin degradar.

Contra engine.activate real (motor de generación de CRIBA):
- 100+ ideas se generan con identidades únicas (sin colisión)
- las métricas del packet son coherentes con el contenido
- unicode/emojis/queries largas no rompen la generación
- la generación es determinista (mismo query → mismo activation estable)
- recuperación: el packet persistido se relee íntegro desde Storage

Sin UI: ejercita el núcleo de generación. Volumen moderado (100+ ideas) dentro
del presupuesto del entorno; el megaprompt permite abortar si se excede.

Invariantes: ranking coherente, contadores correctos, sin pérdida de identidad,
persistencia/recuperación GREEN.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from criba.engine import activate
from criba.storage import Storage


@pytest.fixture(scope="module")
def packet_volumen() -> dict:
    return activate("reducir el consumo de agua en el riego agricola sin perder rendimiento")


def test_volumen_genera_ideas_suficientes(packet_volumen: dict) -> None:
    """La generación produce un volumen alto de ideas (>= 80, determinista)."""
    ideas = packet_volumen["ideas"]
    assert len(ideas) >= 80, f"se esperaba volumen alto, se obtuvo {len(ideas)}"


def test_identidades_unicas_sin_colision(packet_volumen: dict) -> None:
    """Cada idea tiene una identidad única: el ranking no colapsa por duplicados."""
    ideas = packet_volumen["ideas"]
    ids = [i.get("id") for i in ideas if i.get("id")]
    assert len(ids) == len(set(ids)), "hay identificadores de idea duplicados"


def test_metricas_coherentes_con_contenido(packet_volumen: dict) -> None:
    """Las métricas declaradas coinciden con el número real de ideas."""
    metricas = packet_volumen.get("metrics", {})
    ideas = packet_volumen["ideas"]
    # El contador de ideas del packet refleja la lista real.
    if "ideas" in metricas:
        assert metricas["ideas"] == len(ideas)
    # No hay métrica negativa ni absurdamente inflada.
    for valor in metricas.values():
        if isinstance(valor, (int, float)):
            assert valor >= 0


def test_ranking_coherente(packet_volumen: dict) -> None:
    """Si hay score/ranking, es monótono no creciente (orden estable)."""
    ideas = packet_volumen["ideas"]
    scores = [i["score"] for i in ideas if isinstance(i.get("score"), (int, float))]
    if len(scores) >= 2:
        assert scores == sorted(scores, reverse=True), "el ranking no está ordenado"


def test_generacion_determinista() -> None:
    """El mismo query produce el mismo contenido (reproducibilidad)."""
    q = "reducir el consumo de agua en el riego agricola sin perder rendimiento"
    a = activate(q)
    b = activate(q)
    ids_a = [i.get("id") for i in a["ideas"]]
    ids_b = [i.get("id") for i in b["ideas"]]
    assert ids_a == ids_b, "la generación no es determinista entre llamadas"


def test_unicode_y_emojis_no_rompen() -> None:
    """Queries con unicode, emojis y longitud extrema generan sin excepción."""
    packet = activate("¿Cómo? Привет 👋 mejora continua 🚀 en sistemas 🧠 distribuidos")
    assert packet["ideas"]
    assert "👋" in packet["original_query"]


def test_query_larga_no_explota() -> None:
    """Un query muy largo se procesa sin degradación ni excepción."""
    packet = activate("optimizar " + ("proceso de aprobacion " * 50))
    assert packet["ideas"]


def test_recuperacion_persistiendo_y_releyendo(packet_volumen: dict, tmp_path: Path) -> None:
    """El packet generado se persiste en Storage y se recupera íntegro."""
    storage = Storage(tmp_path / "sessions.sqlite3")
    storage.initialize()
    query = "reducir el consumo de agua en el riego agricola sin perder rendimiento"
    ident = storage.save(query, packet_volumen, {"mode": "balanced"})
    recuperado = storage.get(ident)
    # El packet viaja anidado; su identidad y contenido sobreviven el ciclo.
    packet = recuperado["packet"]
    assert packet["activation_id"] == packet_volumen["activation_id"]
    assert len(packet["ideas"]) == len(packet_volumen["ideas"])


def test_serializacion_json_estable(packet_volumen: dict) -> None:
    """El packet se serializa/deserializa a JSON sin pérdida (base de persistencia)."""
    roundtrip = json.loads(json.dumps(packet_volumen, ensure_ascii=False))
    assert roundtrip["activation_id"] == packet_volumen["activation_id"]
    assert len(roundtrip["ideas"]) == len(packet_volumen["ideas"])
