"""CB-S01: cero secretos en artefactos, logs, JSON de verificación y procedencia.

Complementa los tests unitarios ya existentes:
- test_interprete_puerto: sin_secretos() en Provenance y URLs con user:pass@
- test_logging: _redact() anidado, listas, claves sensibles
- test_bank_provenance_cb01: procedencia del banco sin secretos

Este módulo añade el GATE que el megaprompt pide: un escáner que recorre los
artefactos reales de verification/ y el JSON de procedencia, y falla si aparece
un VALOR de credencial (no la palabra 'authorization' suelta, que es benigna).

Patrones buscados (valores, no palabras):
- 'Bearer <token>' con token no vacío
- 'api_key=<valor>' / 'token=<valor>' / 'password=<valor>' con valor real
- 'user:password@host' en una URL
- '"api_key": "<valor-real>"' en JSON

Invariante: ningún artefacto commiteado puede filtrar una credencial.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_CRIBA_ROOT = Path(__file__).resolve().parents[2]
_VERIFICATION_DIR = _CRIBA_ROOT / "verification"

# Valores de credencial reales, NO la palabra suelta.
_BEARER = re.compile(r"Bearer\s+[A-Za-z0-9._\-]{8,}")
_KV_SECRET = re.compile(
    r"\b(api_key|apikey|token|password|secret|access_key)\s*[=:]\s*['\"]?[A-Za-z0-9._\-]{8,}",
    re.IGNORECASE,
)
_URL_CREDS = re.compile(r"://[^\s/:@]+:[^\s/@]+@")
_JSON_SECRET = re.compile(
    r'"(api_key|apikey|token|password|secret|access_key)"\s*:\s*"[^"]{8,}"',
    re.IGNORECASE,
)

# Palabras benignas que NO son secretos (autorización de BLACKFORGE, etc.).
_BENIGNO = re.compile(
    r"authorization_state|authorization_required|_sin_secretos|endpoint_sin_secretos",
    re.IGNORECASE,
)


# Valores que ya están redactados: no son fugas.
_REDACTED = re.compile(r"\[REDACTED?\]|\[REDACTADO\]", re.IGNORECASE)


def _scan(text: str) -> list[str]:
    """Devuelve coincidencias de credenciales reales, excluyendo contexto benigno."""
    hallazgos: list[str] = []
    for patron in (_BEARER, _KV_SECRET, _URL_CREDS, _JSON_SECRET):
        for m in patron.finditer(text):
            inicio = max(0, m.start() - 20)
            contexto = text[inicio:m.end()]
            if _BENIGNO.search(contexto):
                continue
            # Un valor ya redactado no es una fuga.
            if _REDACTED.search(m.group()):
                continue
            hallazgos.append(m.group())
    return hallazgos


def _artifacts() -> list[Path]:
    if not _VERIFICATION_DIR.exists():
        return []
    return sorted(_VERIFICATION_DIR.glob("*.json"))


# --------------------------------------------------------------------------
# Gate sobre artefactos reales de verification/
# --------------------------------------------------------------------------


def test_verification_json_no_filtra_credenciales() -> None:
    """Ningún artefacto JSON de verification/ contiene un valor de credencial."""
    artifacts = _artifacts()
    if not artifacts:
        pytest.skip("no hay artefactos JSON en verification/")
    fugas: list[str] = []
    for artifact in artifacts:
        texto = artifact.read_text(encoding="utf-8")
        for hallazgo in _scan(texto):
            fugas.append(f"{artifact.name}: {hallazgo[:40]}")
    assert not fugas, f"credenciales filtradas en artefactos: {fugas}"


def test_procedencia_del_banco_sin_secretos() -> None:
    """El endpoint con credenciales embebidas se saneado por sanitize_endpoint."""
    import importlib.util

    prov_path = _VERIFICATION_DIR / "_provenance.py"
    if not prov_path.exists():
        pytest.skip("_provenance.py ausente")
    spec = importlib.util.spec_from_file_location("_prov_scan", prov_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Endpoint con credenciales embebidas → saneado.
    sucio = "http://usuario:clave-secreta@host:8642/v1"
    limpio = mod.sanitize_endpoint(sucio)
    assert "clave-secreta" not in limpio
    assert not _scan(limpio), f"endpoint saneado aún filtra: {_scan(limpio)}"


def test_sin_secretos_de_provenance_no_expone_clave() -> None:
    """Provenance.sin_secretos() redacta endpoints con credenciales embebidas."""
    from criba.interprete.puerto import Provenance

    prov = Provenance(
        interpreter_backend="openai_compatible",
        provider="test",
        model_requested="m",
        model_reported="m",
        endpoint="http://user:pass@host/v1?token=secreto123456",
        timestamp="2026-01-01T00:00:00Z",
        duration_ms=1,
        prompt_version="v1",
        schema_version="s1",
        request_id="req-1",
        fallback_used=False,
        raw_output_sha256="a" * 64,
    )
    volcado = json.dumps(prov.sin_secretos(), ensure_ascii=False)
    assert "secreto123456" not in volcado
    assert not _scan(volcado), f"sin_secretos aún filtra: {_scan(volcado)}"


# --------------------------------------------------------------------------
# El patrón del escáner distingue credencial de palabra benigna
# --------------------------------------------------------------------------


def test_escáner_ignora_palabra_benigna() -> None:
    """'authorization_state' y similares no disparan el gate (no son credenciales)."""
    assert _scan('"authorization_state": "pending"') == []
    assert _scan('"endpoint_sin_secretos": "http://host/v1"') == []


def test_escáner_detecta_credencial_real() -> None:
    """El gate SÍ detecta valores de credencial reales."""
    assert _scan("Authorization: Bearer abc123DEF456ghi")
    assert _scan("api_key=supersecreta123")
    assert _scan("http://user:password123@host/v1")
    assert _scan('"api_key": "valor-real-1234"')


def test_logging_redact_anidado() -> None:
    """_redact() del logging elimina secretos en estructuras anidadas y listas."""
    try:
        from criba.logging import _redact
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"_redact no importable: {exc}")
    payload = {
        "config": {"api_key": "secreto-real-1234", "name": "ok"},
        "items": [{"token": "abcdef123456"}],
    }
    resultado = json.dumps(_redact(payload), ensure_ascii=False)
    assert "secreto-real-1234" not in resultado
    assert "abcdef123456" not in resultado
    assert not _scan(resultado)
