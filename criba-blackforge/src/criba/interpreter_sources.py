"""Read-only discovery for Shadow interpreter choices.

Never read Hermes/OpenCode auth stores, launch a provider, or send prompts.
A catalog entry is NOT evidence of free pricing, active auth, or inference.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

_URLS = {
    "hermes": "http://127.0.0.1:8645/v1/models",
    "opencode": "http://127.0.0.1:4096/provider",
    "ollama": "http://127.0.0.1:11434/api/tags",
}
_LIMIT = 1024 * 1024
_MAX_MODELS = 500


@dataclass(frozen=True)
class ModelChoice:
    source: str
    model_id: str
    provider: str = ""
    connected_reported: bool = False


@dataclass(frozen=True)
class SourceCatalog:
    source: str
    models: tuple[ModelChoice, ...]
    note: str


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _strict_json(raw: bytes) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result

    def invalid_constant(value: str) -> Any:
        raise ValueError("invalid JSON constant")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                      parse_constant=invalid_constant)


def _get_local_json(source: str) -> Any:
    """Only three pinned loopback URLs; never honor HTTP proxies or redirects."""
    url = _URLS[source]
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    with opener.open(Request(url, method="GET",
                             headers={"Accept": "application/json"}), timeout=3) as response:
        if response.status != 200:
            raise ValueError("local service returned a non-success status")
        body = response.read(_LIMIT + 1)
    if len(body) > _LIMIT:
        raise ValueError("local catalog exceeds safety limit")
    return _strict_json(body)


def _name(value: Any) -> str:
    if (not isinstance(value, str) or not 0 < len(value) <= 240
            or value != value.strip() or not value.isprintable()
            or "<" in value or ">" in value or "&" in value):
        return ""
    return value


def discover_models(source: str) -> SourceCatalog:
    """Explicit GET-only refresh; never verify subscription or authenticate accounts."""
    if source not in _URLS:
        raise ValueError("unsupported interpreter source")
    try:
        payload = _get_local_json(source)
    except (OSError, HTTPError, URLError, ValueError, UnicodeError) as exc:
        # Do not return exception messages: proxies can include secrets in URLs.
        raise ValueError(
            "Servicio local no disponible o catálogo inválido. "
            "Hermes: hermes proxy start; OpenCode: opencode serve; "
            "Ollama: inicia Ollama. No se han leído credenciales."
        ) from None
    if not isinstance(payload, dict):
        raise ValueError("El catálogo local no es un objeto JSON.")
    models: list[ModelChoice] = []
    seen: set[tuple[str, str]] = set()

    def add(model: Any, provider: str = "", connected: bool = False) -> None:
        name = _name(model)
        origin = _name(provider)
        if not name or len(models) >= _MAX_MODELS or (origin, name) in seen:
            return
        seen.add((origin, name))
        models.append(ModelChoice(source, name, origin, connected))

    if source == "hermes":
        entries = payload.get("data")
        if not isinstance(entries, list):
            raise ValueError("Hermes proxy: /v1/models sin lista data.")
        for entry in entries[:_MAX_MODELS * 2]:
            if isinstance(entry, dict):
                add(entry.get("id"))
        note = "Hermes proxy · catálogo observado; OAuth sigue en Hermes. Precio y acceso NO verificados."
    elif source == "ollama":
        entries = payload.get("models")
        if not isinstance(entries, list):
            raise ValueError("Ollama: /api/tags sin lista models.")
        for entry in entries[:_MAX_MODELS * 2]:
            if isinstance(entry, dict):
                add(entry.get("name") or entry.get("model"))
        note = "Ollama local · modelos anunciados; la aceptación del banco sigue obligatoria."
    else:
        entries = payload.get("all")
        connected_raw = payload.get("connected", [])
        if not isinstance(entries, list) or not isinstance(connected_raw, list):
            raise ValueError("OpenCode: /provider sin lista all/connected.")
        connected = {x for x in connected_raw if isinstance(x, str)}
        for provider in entries[:_MAX_MODELS * 2]:
            if not isinstance(provider, dict):
                continue
            provider_id = _name(provider.get("id"))
            choices = provider.get("models")
            if not provider_id or not isinstance(choices, dict):
                continue
            for model_id in list(choices)[:_MAX_MODELS]:
                add(model_id, provider_id, provider_id in connected)
        note = (
            "OpenCode · catálogo y conexión reportada solamente. "
            "CRIBA aún no tiene adaptador seguro para ejecutar sesiones OpenCode."
        )
    return SourceCatalog(source, tuple(models), note)
