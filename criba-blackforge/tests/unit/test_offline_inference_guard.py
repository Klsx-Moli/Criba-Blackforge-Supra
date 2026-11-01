"""No live model may be reached by the ordinary suite, including loopback models."""

import socket

import pytest


def test_offline_guard_blocks_remote_and_local_provider_before_connect(monkeypatch):
    from tests.offline_inference_guard import OfflineInferenceDenied, install_offline_guard

    sent = []
    monkeypatch.setattr(socket.socket, "connect", lambda *args: sent.append(args))
    monkeypatch.setattr(socket.socket, "connect_ex", lambda *args: sent.append(args))
    install_offline_guard(monkeypatch)
    with socket.socket() as sock:
        for address in [
            ("192.0.2.1", 443),
            ("127.0.0.1", 8645),
            ("localhost", 8080),
            ("::1", 11434),
        ]:
            with pytest.raises(OfflineInferenceDenied):
                sock.connect(address)
            with pytest.raises(OfflineInferenceDenied):
                sock.connect_ex(address)
    assert sent == []


def test_offline_guard_allows_ephemeral_loopback_component_servers(monkeypatch):
    from tests.offline_inference_guard import install_offline_guard

    sent = []
    monkeypatch.setattr(socket.socket, "connect", lambda _self, address: sent.append(address))
    install_offline_guard(monkeypatch)
    with socket.socket() as sock:
        sock.connect(("127.0.0.1", 49153))
    assert sent == [("127.0.0.1", 49153)]
