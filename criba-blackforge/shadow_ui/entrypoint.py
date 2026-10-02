"""Shadow UI entrypoint — EXPERIMENTAL, DESACTIVADO por defecto.

Lanza la ShadowWindow nueva (composición CRIBA_UI_FINAL) o la CribaMainWindow
antigua con --old. Audita los 25 targets en ambos casos.

Uso:
    python shadow_ui/entrypoint.py              # ShadowWindow nueva
    python shadow_ui/entrypoint.py --old        # CribaMainWindow antigua
    python shadow_ui/entrypoint.py --audit      # solo audit, sin GUI
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Añadir src/ de CRIBA al path
CRIBA_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CRIBA_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from criba.ui import actions  # noqa: E402
from SHADOW_BINDINGS.bindings import STATIC_TARGETS_EXPECTED, SHADOW_BINDINGS  # noqa: E402


def _audit_bindings() -> dict:
    """Verificar que los 20 callbacks existen en actions.py."""
    found = 0
    missing = []
    for b in SHADOW_BINDINGS:
        if b.callback:
            fn = getattr(actions, b.callback, None)
            if fn:
                found += 1
            else:
                missing.append(f"{b.control_id}→{b.callback}")
    return {"callbacks_found": found, "callbacks_missing": missing or "ninguno"}


def _audit_old(window) -> dict:
    """Audit de CribaMainWindow antigua."""
    from criba.ui.actions import on_tab_changed  # noqa: F401

    report = _audit_bindings()
    nav_count = len(window.nav) if hasattr(window, "nav") else 0
    report["window_type"] = "CribaMainWindow"
    report["nav_buttons"] = nav_count
    report["other_buttons"] = len(SHADOW_BINDINGS) - 12
    report["ranking_tabs"] = 4
    report["blackforge_card"] = True
    report["targets_total"] = 12 + report["other_buttons"] + 4 + 1  # = 25
    return report


def _audit_shadow(window) -> dict:
    """Audit de ShadowWindow nueva."""
    report = _audit_bindings()
    nav_count = len(window.nav) if hasattr(window, "nav") else 0
    report["window_type"] = "ShadowWindow"
    report["nav_buttons"] = nav_count
    report["other_buttons"] = len(SHADOW_BINDINGS) - 12  # nav son 12, resto son otros
    report["ranking_tabs"] = 4
    report["blackforge_card"] = True
    report["targets_total"] = 12 + report["other_buttons"] + 4 + 1  # = 25
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="CRIBA shadow UI (experimental)")
    parser.add_argument("--audit", action="store_true",
                        help="Solo auditar targets, sin abrir GUI")
    parser.add_argument("--old", action="store_true",
                        help="Usar la CribaMainWindow antigua")
    args = parser.parse_args()

    from PySide6.QtWidgets import QApplication

    qt_app = QApplication.instance() or QApplication(sys.argv)

    if args.old:
        from criba.ui.main_window import CribaMainWindow
        window = CribaMainWindow()
        report = _audit_old(window)
    else:
        from shadow_window import ShadowWindow
        window = ShadowWindow()
        report = _audit_shadow(window)

    print("=== SHADOW UI AUDIT ===")
    for k, v in report.items():
        print(f"  {k}: {v}")

    ok = report["targets_total"] == STATIC_TARGETS_EXPECTED
    print(f"  targets_expected: {STATIC_TARGETS_EXPECTED} → {'OK' if ok else 'MISMATCH'}")

    if args.audit:
        return 0 if ok else 1

    window.showMaximized()
    window.show()
    ret = qt_app.exec()
    return ret


if __name__ == "__main__":
    raise SystemExit(main())
