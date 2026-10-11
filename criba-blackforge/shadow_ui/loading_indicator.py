"""User-supplied APNG frames, decoded losslessly at asset preparation time.

Qt's installed PNG reader only reads APNG's first frame. Sprite sheets retain
all composited RGBA frames without adding a runtime decoding dependency.
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class LoadingIndicator(QWidget):
    def __init__(self, resource: str, size: QSize, parent=None) -> None:
        super().__init__(parent)
        root = Path(__file__).parent / "assets" / "loading"
        metadata = json.loads((root / f"{resource}.json").read_text(encoding="utf-8"))
        sheet = QPixmap(str(root / f"{resource}_frames.png"))
        if sheet.isNull():
            raise RuntimeError(f"Missing animation resource: {resource}")
        width, height = metadata["size"]
        columns = metadata["columns"]
        self.frames = [
            sheet.copy((i % columns) * width, (i // columns) * height, width, height)
            .scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            for i in range(metadata["count"])
        ]
        self.durations = metadata["durations"]
        self.index = 0
        self.operations: dict[object, str] = {}
        self.reduced_motion = False
        self.image = QLabel(self)
        self.image.setFixedSize(size)
        self.image.setAlignment(Qt.AlignCenter)
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image)
        layout.addWidget(self.label, 1)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._advance)
        # Retain the slot while idle to prevent layout jumps.
        policy = self.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.setSizePolicy(policy)
        self.hide()

    def begin(self, token: object, text: str) -> None:
        self.operations[token] = text
        self.label.setText(text)
        self.setAccessibleName(text)
        self.image.setPixmap(self.frames[self.index])
        self.show()
        self._schedule()

    def finish(self, token: object) -> None:
        self.operations.pop(token, None)
        if self.operations:
            self.label.setText(next(reversed(self.operations.values())))
        else:
            self.timer.stop()
            self.index = 0
            self.hide()

    def _schedule(self) -> None:
        if self.operations and self.isVisible() and not self.reduced_motion:
            self.timer.start(round(self.durations[self.index]))

    def _advance(self) -> None:
        self.index = (self.index + 1) % len(self.frames)
        self.image.setPixmap(self.frames[self.index])
        self._schedule()

    def hideEvent(self, event) -> None:
        self.timer.stop()
        super().hideEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._schedule()
