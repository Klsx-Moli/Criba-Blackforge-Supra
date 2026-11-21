"""Process-local network boundary for the ordinary test suite, not product code."""

from __future__ import annotations

import ipaddress
import socket


class OfflineInferenceDenied(OSError):
    """The suite attempted non-component networking without guarded live opt-in."""


def install_offline_guard(monkeypatch, *, live_proxy=False):
    original = socket.socket.connect
    original_ex = socket.socket.connect_ex

    def check(address):
        if not isinstance(address, tuple) or len(address) < 2:
            return  # AF_UNIX / Windows pipes, not an Internet connection
        host, port = str(address[0]).lower(), address[1]
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host == "localhost"
        blocked_model_port = port in {8080, 11434} or (port == 8645 and not live_proxy)
        if not loopback or blocked_model_port:
            raise OfflineInferenceDenied("Ordinary tests cannot contact real model providers")

    def connect(sock, address):
        check(address)
        return original(sock, address)

    def connect_ex(sock, address):
        check(address)
        return original_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
