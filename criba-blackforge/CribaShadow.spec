# -*- mode: python ; coding: utf-8 -*-
"""Spec de CribaShadow.exe — paquete LOCAL de prueba, no una release.

Se entrega como carpeta con sus dependencias y recursos (onedir), que es lo
que el encargo pide: no hace falta instalador ni un unico archivo, y no es un
acceso directo disfrazado de aplicacion.

Los assets de Shadow UI se resuelven por Path(__file__).parent / "assets", asi
que van en la raiz del bundle para que esa ruta siga siendo cierta dentro del
ejecutable.
"""
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(os.path.abspath(SPECPATH))
SUPRA_SRC = ROOT.parent / "supra" / "src"

a = Analysis(
    [str(ROOT / "criba_shadow_main.py")],
    pathex=[
        str(ROOT),
        str(ROOT / "src"),
        str(ROOT / "shadow_ui"),
        str(ROOT / "shadow_ui" / "SHADOW_BINDINGS"),
        str(SUPRA_SRC),
    ],
    binaries=[],
    datas=[
        # Shadow UI: los assets se resuelven por Path(__file__).parent / "assets",
        # asi que van en la raiz del bundle.
        (str(ROOT / "shadow_ui" / "assets"), "assets"),
        (str(ROOT / "shadow_ui" / "design.tokens.json"), "."),
        (str(ROOT / "shadow_ui" / "GENERATED" / "ui" / "styles.qss"), "."),
        # criba.constants._resolve_data_root() en modo frozen devuelve
        # _MEIPASS/"data", y de ahi saca theme_criba.json (tokens.py). data/ vive
        # en la raiz del repo, NO dentro del paquete criba, asi que
        # collect_data_files("criba", subdir="data") no encontraba nada y el
        # .exe reventaba con FileNotFoundError: theme_criba.json.
        (str(ROOT / "data"), "data"),
        (str(ROOT / "schemas"), "schemas"),
    ],
    hiddenimports=[
        # Shadow UI: modulos sueltos, no visibles para el analisis estatico
        "shadow_window",
        "shadow_context",
        "SHADOW_BINDINGS",
        "SHADOW_BINDINGS.bindings",
        # SUPRA completo: el exe arranca el servidor real
        "supra_agentic",
        "supra_agentic.service",
        "supra_agentic.state",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.server",
        # UI de CRIBA
        "criba",
        "criba.storage",
        "criba.constants",
        "criba.ui",
        "criba.ui.actions",
        "criba.ui.i18n",
        "criba.ui.interpreter",
        "criba.ui.ranking",
        "criba.ui.theme",
        "criba.ui.tokens",
        "criba.ui.widgets",
        "criba.ui.panels",
        "criba.ui.dialogs",
        "criba.ui.blackforge_screen",
        "criba.integrations",
        "criba.integrations.supra_client",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtNetwork",
    ]
    + collect_submodules("supra_agentic")
    + collect_submodules("criba.integrations"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # BLACKFORGE no es requisito de este paquete y su llave fisica tampoco.
        # Se excluye su pantalla para que el ejecutable no dependa de ella.
        "blackforge",
        "pytest",
        "_pytest",
        "matplotlib",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CribaShadow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # upx mete falseos de antivirus en un exe de escritorio
    console=False,  # es una app de ventana; los errores se muestran en un dialogo
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CribaShadow",
)