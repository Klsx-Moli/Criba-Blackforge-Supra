"""Capability bridge — BINDING != IMPLEMENTATION.

Widgets call bridge.register(capability_id, callback) to inject
real business logic. The bridge does NOT guess implementation.
States: REGISTERED, UNREGISTERED, BROKEN.
"""
from __future__ import annotations

from typing import Any, Callable


class CapabilityBridge:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable] = {}
        self._states: dict[str, str] = {}

    def register(self, capability_id: str, callback: Callable) -> None:
        self._handlers[capability_id] = callback
        self._states[capability_id] = 'REGISTERED'

    def call(self, capability_id: str, data: dict[str, Any] | None = None) -> Any:
        fn = self._handlers.get(capability_id)
        if fn is None:
            self._states[capability_id] = 'UNREGISTERED'
            return None
        try:
            return fn(data or {})
        except Exception as e:
            self._states[capability_id] = 'BROKEN'
            raise

    def has_handler(self, capability_id: str) -> bool:
        return capability_id in self._handlers

    def get_state(self, capability_id: str) -> str:
        return self._states.get(capability_id, 'UNREGISTERED')
