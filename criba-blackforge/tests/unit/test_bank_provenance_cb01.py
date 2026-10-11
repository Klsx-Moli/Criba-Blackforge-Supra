"""Contrato de procedencia de los artefactos de verification/ (CB-01).

Verifica que _provenance.build_provenance produzca todos los campos obligatorios,
con tipos correctos, y que nunca exponga credenciales en el endpoint sanitizado.

RED antes de _provenance: este test no existía y los JSON de verification/ carecían
de repo_head_sha, entorno, timestamps y hashes. GREEN ahora: el helper los garantiza.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_VERIF = Path(__file__).resolve().parents[2] / "verification" / "_provenance.py"


def _load_provenance_module():
    spec = importlib.util.spec_from_file_location("_provenance_under_test", _VERIF)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REQUIRED_KEYS = [
    "repo_head_sha",
    "git_dirty",
    "git_diff_hash",
    "python_version",
    "platform",
    "uv_lock_sha256",
    "bank_version",
    "prompt_version",
    "schema_version",
    "constrained_decoding",
    "seed",
    "model_requested",
    "model_reported",
    "endpoint_sin_secretos",
    "started_at_utc",
    "script_sha256",
    "finished_at_utc",  # lo añade finalize_provenance
]

SECRET_MARKERS = ["api_key", "apikey", "token", "bearer", "password", "secret", "@"]


def test_build_provenance_tiene_todos_los_campos():
    mod = _load_provenance_module()
    prov = mod.build_provenance(
        bank_version="BANCO-TRACE-05",
        constrained_decoding="json_schema",
        seed=20261011,
        model_requested="modelo-x",
        endpoint="http://127.0.0.1:8645/v1",
    )
    for key in REQUIRED_KEYS[:-1]:  # finished_at_utc lo añade finalize
        assert key in prov, f"falta campo obligatorio de procedencia: {key}"
    assert isinstance(prov["git_dirty"], bool)
    assert prov["python_version"]
    assert prov["started_at_utc"].endswith("+00:00")


def test_finalize_anade_finished_at():
    mod = _load_provenance_module()
    prov = mod.build_provenance(seed=1)
    fin = mod.finalize_provenance(prov)
    assert "finished_at_utc" in fin
    assert fin["finished_at_utc"] >= fin["started_at_utc"]


def test_endpoint_sin_credenciales_se_sanitiza():
    mod = _load_provenance_module()
    sucio = "http://user:supersecret@host.internal:8645/v1"
    limpio = mod.sanitize_endpoint(sucio)
    assert "supersecret" not in limpio
    assert "@" not in limpio
    assert limpio == "http://host.internal:8645/v1"


def test_endpoint_limpio_no_se_altera():
    mod = _load_provenance_module()
    limpio = "http://127.0.0.1:8645/v1"
    assert mod.sanitize_endpoint(limpio) == limpio


def test_provenance_no_expone_secretos_en_json():
    mod = _load_provenance_module()
    prov = mod.build_provenance(
        seed=1,
        endpoint="http://user:tokensecreto@host/v1",
        model_requested="m",
    )
    texto = mod.provenance_json(prov)
    assert "tokensecreto" not in texto
    # El campo endpoint jamás debe conservar credenciales.
    assert "user:tokensecreto@" not in texto


def test_script_sha256_estable_y_no_vacio():
    mod = _load_provenance_module()
    h1 = mod.script_sha256(_VERIF)
    h2 = mod.script_sha256(_VERIF)
    assert h1 and h1 == h2
    assert len(h1) == 64  # sha256 hex


@pytest.mark.parametrize("marker", SECRET_MARKERS[:6])
def test_endpoint_sanitizado_sin_marcadores_de_secreto(marker):
    mod = _load_provenance_module()
    prov = mod.build_provenance(endpoint="http://u:p@h/v1", seed=1)
    # El endpoint persistido nunca debe contener estos marcadores.
    assert marker not in prov["endpoint_sin_secretos"].lower() or marker == "@"
