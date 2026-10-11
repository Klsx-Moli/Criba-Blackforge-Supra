"""Main window — loads generated UI and wires bindings."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import Qt

from ui.generated_ui import build_ui
from runtime.capability_bridge import CapabilityBridge

ROOT = Path(__file__).resolve().parent


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bridge = CapabilityBridge()
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        build_ui(self, layout, self.bridge)
