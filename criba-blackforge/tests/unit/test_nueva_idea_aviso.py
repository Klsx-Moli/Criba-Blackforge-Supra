"""Regresion: pulsar 'Definir problema' con el campo vacio debe avisar.

Defecto reproducido en el .exe empaquetado (2026-11-21):

  dialogs.ask_problem devuelve `text or None` cuando el QTextEdit esta vacio, y
  actions.on_nueva_idea hace `if not problem: return` sin informar. El usuario
  pulsa "Definir problema", el dialogo se cierra y no ocurre nada: el estado
  sigue "Sin iniciar" y no hay ningun mensaje. Parece un cuelgue.

Criterio de aceptacion: el camino sin dialogo (el que usan los tests y la CLI)
y el camino con dialogo deben dejar constancia del rechazo. Se comprueba el
contrato del helper que decide, para no depender de un QDialog modal.
"""
from __future__ import annotations

import sys


class _Banner:
    def __init__(self) -> None:
        self.text = ""
        self.shown = 0

    def setText(self, value: str) -> None:  # noqa: N802 - API Qt
        self.text = value

    def show(self) -> None:
        self.shown += 1


class _NavBtn:
    def __init__(self) -> None:
        self.checked = True

    def setChecked(self, value: bool) -> None:  # noqa: N802 - API Qt
        self.checked = value


class _Win:
    def __init__(self) -> None:
        self.errorBannerText = _Banner()
        self.errorBanner = self.errorBannerText
        self.nav = {"navNuevaIdea": _NavBtn()}
        # _apply_new_problem toca refs["stages"]; el stub lo deja vacio.
        self.refs: dict[str, object] = {}


def test_campo_vacio_avisa_en_lugar_de_ignorar():
    """El helper que decide debe rechazar y avisar, no callarse."""
    from criba.ui.actions import rechazar_problema_vacio

    win = _Win()
    rechazar_problema_vacio(win, "")
    assert win.errorBannerText.text, (
        "pulsar con el campo vacio no produjo ningun aviso: "
        f"banner={win.errorBannerText.text!r} shown={win.errorBanner.shown}"
    )
    assert win.errorBanner.shown >= 1, "el aviso se escribio pero no se mostro"


def test_solo_espacios_tambien_avisa():
    from criba.ui.actions import rechazar_problema_vacio

    win = _Win()
    rechazar_problema_vacio(win, "   \n\t  ")
    assert win.errorBannerText.text, "un problema en blanco debe avisar igual"


def test_el_aviso_menciona_el_problema_base():
    from criba.ui.actions import rechazar_problema_vacio

    win = _Win()
    rechazar_problema_vacio(win, "")
    mensaje = win.errorBannerText.text.lower()
    assert "problema" in mensaje, f"el aviso no dice que falta: {win.errorBannerText.text!r}"


def test_con_problema_valido_no_avisa_error():
    """No debe aparecer un falso positivo al definir de verdad."""
    from criba.ui.actions import rechazar_problema_vacio

    win = _Win()
    rechazar_problema_vacio(win, "Reducir el consumo de agua sin subir la factura")
    assert not win.errorBannerText.text, (
        f"un problema valido disparo el banner de error: {win.errorBannerText.text!r}"
    )


def test_el_aviso_es_una_linea_corta():
    """El banner recorta a 160 chars y toma la primera linea: debe caber."""
    from criba.ui.actions import rechazar_problema_vacio

    win = _Win()
    rechazar_problema_vacio(win, "")
    assert len(win.errorBannerText.text) <= 200, (
        f"aviso demasiado largo para el banner: {len(win.errorBannerText.text)}"
    )


if __name__ == "__main__":
    fallos = 0
    for nombre, fn in sorted(globals().items()):
        if not nombre.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS {nombre}")
        except Exception as exc:
            fallos += 1
            print(f"  FAIL {nombre}: {type(exc).__name__}: {exc}")
    print(f"\nRESULTADO: {fallos} fallos")
    sys.exit(1 if fallos else 0)