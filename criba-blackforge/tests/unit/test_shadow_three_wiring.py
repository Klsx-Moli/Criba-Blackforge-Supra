"""Shadow UI cablea de verdad las tres capacidades que estaban ausentes.

Contexto: navNuevaIdea, navGenerar y btnHibrido estaban DECLARADOS en
SHADOW_BINDINGS/bindings.py y el gate de targets daba 26/26 OK, pero Shadow no
construia los widgets. El gate contaba bindings declarados con un literal 12
para nav, no widgets reales, asi que decia OK mientras faltaban targets.

Estos tests son el centinela de esa clase de fallo. Fallan si:
  - el widget desaparece de la composicion,
  - el handler deja de ser el correcto (callbacks cruzados),
  - el click no llega al handler,
  - el click dispara el handler MAS de una vez (registro duplicado),
  - desaparece la clave i18n que rotula el control.

Mutation sentinel: borrar una entrada de NAV_ITEMS, cambiar un callback_map o
quitar el connect del boton hibrido pone este fichero en rojo.
"""

from __future__ import annotations

import os
import pathlib
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "shadow_ui"))
sys.path.insert(0, str(_ROOT / "shadow_ui" / "SHADOW_BINDINGS"))
sys.path.insert(0, str(_ROOT.parent / "supra" / "src"))

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def win(qapp, monkeypatch):
    """ShadowWindow con los tres handlers espiados, sin ejecutar su logica.

    Se sustituyen los callbacks reales para poder contar llamadas sin lanzar
    workers ni tocar SUPRA: lo que se verifica aqui es el CABLEADO, no el
    efecto. La ejecucion real se prueba aparte en test_shadow_three_wiring_exec.
    """
    from criba.ui import actions
    import shadow_window as sw

    calls: list[str] = []

    def _spy(name):
        def _inner(_win):
            calls.append(name)

        return _inner

    for name in ("on_nueva_idea", "on_generar", "on_hibrido"):
        monkeypatch.setattr(actions, name, _spy(name))

    window = sw.ShadowWindow()
    window._spy_calls = calls  # type: ignore[attr-defined]
    return window


# --------------------------------------------------------------------------
# 1. El widget existe (no basta con que el binding este declarado)
# --------------------------------------------------------------------------

def test_nav_nueva_idea_existe_en_la_navegacion(win) -> None:
    assert "navNuevaIdea" in win.nav, (
        "navNuevaIdea no esta en el nav real; el binding esta declarado pero "
        "el widget no se construye"
    )


def test_nav_generar_existe_en_la_navegacion(win) -> None:
    assert "navGenerar" in win.nav, (
        "navGenerar no esta en el nav real; el binding esta declarado pero "
        "el widget no se construye"
    )


def test_boton_hibrido_existe_en_topcards(win) -> None:
    assert hasattr(win.topcards, "btn_hibrido"), (
        "btnHibrido esta declarado en SHADOW_BINDINGS pero Shadow no construye "
        "el boton: el trabajo hibrido queda inalcanzable desde la interfaz"
    )


def test_los_doce_nav_estan_presentes(win) -> None:
    esperados = {
        "navNuevaIdea",
        "navGenerar",
        "navInventar",
        "navEvaluar",
        "navRed",
        "navBlackforge",
        "navSupra",
        "navTecnicas",
        "navModelos",
        "navHistorial",
        "navRetro",
        "navMemoria",
    }
    assert esperados <= set(win.nav), (
        f"faltan nav: {sorted(esperados - set(win.nav))}"
    )


# --------------------------------------------------------------------------
# 2. El handler es el correcto (detecta callbacks cruzados)
# --------------------------------------------------------------------------

def test_nav_nueva_idea_llama_a_on_nueva_idea(win) -> None:
    win._nav("navNuevaIdea")
    assert win._spy_calls == ["on_nueva_idea"], (
        f"navNuevaIdea llamo a {win._spy_calls}, se esperaba ['on_nueva_idea']"
    )


def test_nav_generar_llama_a_on_generar(win) -> None:
    win._nav("navGenerar")
    assert win._spy_calls == ["on_generar"], (
        f"navGenerar llamo a {win._spy_calls}, se esperaba ['on_generar']"
    )


def test_boton_hibrido_llama_a_on_hibrido(win) -> None:
    win.topcards.btn_hibrido.click()
    assert win._spy_calls == ["on_hibrido"], (
        f"btn_hibrido llamo a {win._spy_calls}, se esperaba ['on_hibrido']"
    )


# --------------------------------------------------------------------------
# 3. No hay registro duplicado
# --------------------------------------------------------------------------

def test_nav_nueva_idea_no_duplica_llamada(win) -> None:
    win._nav("navNuevaIdea")
    win._nav("navNuevaIdea")
    assert win._spy_calls == ["on_nueva_idea", "on_nueva_idea"], (
        f"se esperaban 2 llamadas exactas, hubo {win._spy_calls}"
    )


def test_boton_hibrido_dispara_una_sola_vez(win) -> None:
    win.topcards.btn_hibrido.click()
    win.topcards.btn_hibrido.click()
    assert win._spy_calls.count("on_hibrido") == 2, (
        f"2 clicks debian dar 2 llamadas, hubo {win._spy_calls.count('on_hibrido')}"
    )


def test_los_tres_controles_no_se_contaminan_entre_si(win) -> None:
    """Cada control debe llamar a SU handler y solo al suyo."""
    win._nav("navNuevaIdea")
    win._nav("navGenerar")
    win.topcards.btn_hibrido.click()
    assert win._spy_calls == ["on_nueva_idea", "on_generar", "on_hibrido"], (
        f"contaminacion entre controles: {win._spy_calls}"
    )


# --------------------------------------------------------------------------
# 4. Rotulado i18n presente (un control sin texto es un control roto)
# --------------------------------------------------------------------------

def test_las_claves_i18n_de_los_tres_controles_existen() -> None:
    from criba.ui import i18n

    claves = [
        "shadow.nav.nueva_idea",
        "shadow.nav.nueva_idea.sub",
        "shadow.nav.generar",
        "shadow.nav.generar.sub",
        "shadow.hibrido",
    ]
    for tabla_id, tabla in i18n._STRINGS.items():
        for clave in claves:
            assert clave in tabla, (
                f"falta {clave} en la tabla {tabla_id}: el control se "
                f"rotularia con la clave cruda"
            )


def test_los_tres_controles_no_mostraran_clave_cruda(win) -> None:
    """El texto renderizado no puede ser la propia clave i18n."""
    textos = [
        win.nav["navNuevaIdea"].button.text(),
        win.nav["navGenerar"].button.text(),
        win.topcards.btn_hibrido.text(),
    ]
    for texto in textos:
        assert texto and "shadow." not in texto, (
            f"control rotulado con clave cruda: {texto!r}"
        )


# --------------------------------------------------------------------------
# 5. Los handlers existen de verdad en actions.py
# --------------------------------------------------------------------------

def test_los_tres_handlers_existen_en_actions() -> None:
    from criba.ui import actions

    for nombre in ("on_nueva_idea", "on_generar", "on_hibrido"):
        assert callable(getattr(actions, nombre, None)), (
            f"actions.{nombre} no existe o no es llamable"
        )


def test_los_tres_bindings_declarados_tienen_handler() -> None:
    """ Ningun ShadowBinding puede apuntar a un callback inexistente. """
    import importlib

    bindings_mod = importlib.import_module("SHADOW_BINDINGS.bindings")
    from criba.ui import actions

    huerfanos = [
        b.control_id
        for b in bindings_mod.SHADOW_BINDINGS
        if b.callback and not callable(getattr(actions, b.callback, None))
    ]
    assert not huerfanos, f"bindings sin handler real: {huerfanos}"