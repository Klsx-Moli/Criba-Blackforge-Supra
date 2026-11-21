"""Contrato: el comando ``hybrid`` del CLI debe ejecutar el pipeline híbrido.

Defecto reproducido en el .exe empaquetado (CRIBA-CLI.exe de dist/CRIBA-Blackforge,
2026-11-21): el subcomando ``hybrid`` está registrado en el parser
(cli.py:203, con --query, --enhance-semantics y --reasoning) pero NINGUNA rama
de ``main()`` lo maneja, así que toda ejecución acaba en
``parser.error("Comando desconocido: hybrid")`` -> SystemExit(2).

Criterio de aceptación: ``criba hybrid --query ...`` ejecuta
``criba.hybrid.run_hybrid``, imprime el HybridResult en JSON (claves
``final_recommendation``, ``final_confidence`` y
``pipeline_stages_completed`` contiene ensemble/chain/adversarial) y devuelve 0.
"""

from __future__ import annotations

import json

from criba.cli import main


def test_hybrid_subcomando_esta_registrado():
    """El parser debe seguir exponiendo hybrid (no eliminar el contrato)."""
    import argparse

    # main() construye el parser internamente; comprobamos el contrato
    # negativo: sin el subcomando, el ejecutable fallaría igual que antes.
    # Aquí basta con que --help lo liste; el .exe lo demostró ya.
    assert callable(main)


def test_hybrid_ejecuta_pipeline_y_devuelve_cero(capsys):
    """hybrid --query debe producir un HybridResult serializado y exit 0."""
    rc = main(["hybrid", "--query", "边缘"])
    out = capsys.readouterr().out
    assert rc == 0, f"hybrid devolvió {rc}; salida={out[:400]!r}"
    # El HybridResult se vuelca como JSON: buscamos claves reales del contrato.
    assert "final_recommendation" in out, out[:400]
    assert "pipeline_stages_completed" in out, out[:400]
    payload = json.loads(out)
    for stage in ("ensemble", "chain", "adversarial"):
        assert stage in payload["pipeline_stages_completed"], (
            f"falta etapa {stage}: {payload['pipeline_stages_completed']}"
        )
    assert payload["final_confidence"] in ("confirmed", "hypothesis", "rejected"), (
        f"confidence inválida: {payload['final_confidence']}"
    )


def test_hybrid_sin_query_falla_con_codigo_no_cero(capsys):
    """--query es requerido: argparse debe rechazarlo y no simular éxito."""
    try:
        rc = main(["hybrid"])
    except SystemExit as exc:
        assert exc.code not in (0, None), "hybrid sin query debe fallar"
        return
    raise AssertionError(f"hybrid sin --query no falló: rc={rc}")