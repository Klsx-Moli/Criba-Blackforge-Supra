"""Binding runtime — maps UI events to capability bridge calls."""
from __future__ import annotations


class BindingRuntime:
    def __init__(self, bridge):
        self.bridge = bridge

    def wire(self, widget, capability_id, method='POST'):
        from PySide6.QtWidgets import QPushButton
        if isinstance(widget, QPushButton):
            widget.clicked.connect(lambda: self.bridge.call(capability_id))
