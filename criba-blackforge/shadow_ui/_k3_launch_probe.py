"""Comprobacion minima K3: ShadowWindow se CONSTRUYE sin BLACKFORGE obligatorio.

No abre GUI visible (eso exige escritorio/operador). Verifica que el arranque
real (QApplication + ShadowWindow) no muere ni exige BLACKFORGE, que es el
criterio K3 "CRIBA/SUPRA sin inicializacion obligatoria de BLACKFORGE" en su
parte demostrable sin intervencion visual. Qt corre en offscreen aqui: el
criterio "arranque VISIBLE en Windows" lo cierra el operador viendo la ventana.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

qt_app = QApplication.instance() or QApplication(sys.argv)
bf_modules = [m for m in sys.modules if "blackforge" in m.lower()]
print("BLACKFORGE_MODULES_LOADED_BEFORE:", bf_modules)

from shadow_window import ShadowWindow
window = ShadowWindow()
print("SHADOW_WINDOW_CONSTRUCTED:", type(window).__name__)

bf_after = [m for m in sys.modules if "blackforge" in m.lower()]
print("BLACKFORGE_MODULES_LOADED_AFTER:", bf_after)

# Cerrar sola: no depende de que un humano cierre la ventana.
QTimer.singleShot(1500, qt_app.quit)
window.show()
rc = qt_app.exec()
print("QT_EXEC_RC:", rc)
print("RESULT: ShadowWindow construida y arranco; BLACKFORGE exigido:",
      "NO" if not bf_after else "SI -> INCUMPLE")
