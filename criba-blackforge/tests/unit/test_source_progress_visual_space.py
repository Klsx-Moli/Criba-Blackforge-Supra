"""Sentinel: el indicador de «Actualizar fuentes» debe USAR el espacio físico.

Defecto reproducido el 2026-10-05 por sonda (`probe_visual.py`): el HUD era
`setFixedSize(48, 48)` y la lista de fuentes `setMaximumHeight(102)`, así que
un panel de 1400 px mostraba el mismologo de 48 px y la misma lista de 102 px.
El contador «N fuentes» avanzaba, pero el espacio era decorado, no usado.

Credenciales de este sentinel (probadas por mutación, no por lectura):
- Volver `NeonHUD` a `setFixedSize(48, 48)`     -> test_hud_is_not_pinned_to_a_fixed_size ROJO.
- Quitar el `scale` en `paintEvent`             -> test_hud_paints_at_its_rendered_size ROJO.
- Volver el scroll a `setMaximumHeight(102)`    -> test_source_list_uses_available_height ROJO.
- Dejar `current_query` oculto                 -> test_running_source_and_query_are_visible ROJO.

Ambas aserciones son sobre widgets VIVOS: `isVisible()` + `size()`, no sólo texto.
Un `.text()` correcto en un widget oculto no acredita nada.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

pytest.importorskip("PySide6.QtWidgets")

from criba.ui import source_progress as sp


@pytest.fixture(scope="module")
def app():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    instance = QApplication.instance() or QApplication(sys.argv)
    yield instance
    instance.processEvents()


def _panel(app, *, width: int, height: int):
    panel = sp.SourceProgress()
    panel.resize(width, height)
    panel.show()
    app.processEvents()
    return panel


def test_hud_is_not_pinned_to_a_fixed_size(app) -> None:
    """El logo se dimensiona con el espacio; 48x48 fijo es el defecto."""
    panel = _panel(app, width=320, height=900)
    try:
        # `setFixedSize` se manifiesta como minimum == maximum; `isFixedSize()` no
        # existe en PySide6, asi que se comprueba la invariante que el fija.
        assert panel.hud.minimumWidth() != panel.hud.maximumWidth(), (
            f"HUD fijado en {panel.hud.minimumWidth()}px: no puede aprovechar el espacio"
        )
        assert panel.hud.minimumWidth() == sp.HUD_MIN
        assert panel.hud.maximumWidth() == sp.HUD_MAX
        edge = panel.hud.size().width()
        assert edge > sp.HUD_REFERENCE, (
            f"HUD no crece: {edge}px con {panel.height()}px disponibles "
            f"(referencia {sp.HUD_REFERENCE}px)"
        )
    finally:
        panel.close()
        panel.deleteLater()


def test_hud_paints_at_its_rendered_size(app) -> None:
    """Un logo pequeno dentro de un widget grande es el logo recortado, no el logo.

    Mide el rectangulo envolvente REAL de los pixeles pintados: si `scale` no se
    aplica, el trazo queda en el 48px centrales y mide ~1/3 del widget.
    """
    panel = _panel(app, width=320, height=900)
    try:
        image = panel.hud.grab().toImage()
        width, height = image.width(), image.height()
        assert (width, height) == (panel.hud.width(), panel.hud.height())

        background = image.pixelColor(0, 0)
        min_x, min_y, max_x, max_y = width, height, -1, -1
        painted = 0
        for x in range(width):
            for y in range(height):
                color = image.pixelColor(x, y)
                delta = max(
                    abs(color.red() - background.red()),
                    abs(color.green() - background.green()),
                    abs(color.blue() - background.blue()),
                )
                if delta > 24:
                    painted += 1
                    min_x, max_x = min(min_x, x), max(max_x, x)
                    min_y, max_y = min(min_y, y), max(max_y, y)
        assert painted, "el logo no pinta nada"
        span_x, span_y = max_x - min_x, max_y - min_y
        assert span_x / width > 0.75, (
            f"el logo no escala con el widget: ocupa {span_x}px de {width} "
            f"({span_x / width:.0%}); esta recortado alTamano de referencia"
        )
        assert span_y / height > 0.75, (
            f"el logo no escala con el widget: ocupa {span_y}px de {height} "
            f"({span_y / height:.0%})"
        )
    finally:
        panel.close()
        panel.deleteLater()


def test_source_list_uses_available_height(app) -> None:
    """La lista por fuente no puede seguir topada a un máximo de 102 px."""
    panel = _panel(app, width=320, height=900)
    try:
        ceiling = panel.scroll_area.maximumHeight()
        assert ceiling > 1000, f"lista de fuentes topada a {ceiling}px: ignora el espacio"
        assert panel.scroll_area.height() > 200, (
            f"la lista sólo ocupa {panel.scroll_area.height()}px de {panel.height()}"
        )
    finally:
        panel.close()
        panel.deleteLater()


def test_running_source_and_query_are_visible(app) -> None:
    """El usuario pidió VER la fuente en curso, no deducirla de un contador."""
    panel = _panel(app, width=420, height=900)
    try:
        panel.begin()
        app.processEvents()
        panel.update_progress(
            {
                "phase": "query_started",
                "source_id": "github",
                "state": "querying",
                "query": "ortogonal causalidadinnnovacion",
                "completed_queries": 0,
                "total_queries": 1,
            }
        )
        app.processEvents()
        assert panel.current_query.isVisible(), "la consulta en curso no se muestra"
        shown = panel.current_query.text()
        assert "GitHub" in shown, f"la fuente en curso no se nombra: {shown!r}"
        assert "causalidad" in shown, f"la consulta en curso no se muestra: {shown!r}"
    finally:
        panel.close()
        panel.deleteLater()


def test_per_source_rows_expose_real_states(app) -> None:
    """Cada fuente tiene fila visible con estado real, no un contador agregado."""
    panel = _panel(app, width=420, height=900)
    try:
        panel.begin()
        panel.update_progress(
            {
                "phase": "started",
                "source_id": "",
                "source_ids": ["crossref", "github"],
                "state": "running",
                "completed_queries": 0,
                "total_queries": 2,
            }
        )
        panel.update_progress(
            {
                "phase": "source_completed",
                "source_id": "crossref",
                "state": "success",
                "summary": {
                    "documents": 7,
                    "errores": 0,
                    "cached_queries": 0,
                    "network_queries": 1,
                    "errors": [],
                },
                "completed_queries": 1,
                "total_queries": 2,
            }
        )
        app.processEvents()
        assert set(panel.rows) == {"crossref", "github"}
        for source_id, (name, status) in panel.rows.items():
            assert name.isVisible(), f"fila de {source_id} no visible"
            assert status.isVisible(), f"estado de {source_id} no visible"
            assert status.text().strip(), f"estado vacío para {source_id}"
        assert "7" in panel.rows["crossref"][1].text()
        assert panel.states["crossref"] == "success"
    finally:
        panel.close()
        panel.deleteLater()


def test_i18n_current_query_defined_in_both_languages() -> None:
    """Una clave ausente se renderiza CRUDA en la ventana viva."""
    from criba.ui import i18n

    for lang, table in i18n._STRINGS.items():
        assert "sources.current_query" in table, f"{lang} sin sources.current_query"
        assert "{source}" in table["sources.current_query"]
        assert "{query}" in table["sources.current_query"]
        assert str(table["sources.current_query"]).strip()


def test_module_path_is_importable_from_repo_root() -> None:
    """El sentinel no debe pasar si el módulo desapareció del paquete."""
    assert pathlib.Path(sp.__file__).exists()
