"""Exercise actual profile-to-request wiring and generation-policy cache isolation."""

import json
from importlib.metadata import version

from criba import __version__
from criba.api import Handler
from criba.interprete import openai_compatible as oc
from criba.interprete.juez import JuezInterprete
from criba.interprete.store import InterpreteStore
from criba.model_config import ModelProfile, ModelSettings, save_model_settings
from criba.storage import Storage
from test_interpreter_hardening import IDEA, respuesta, transporte

from verification.interpreter_cases import critica, propuesta


def test_local_profile_controls_real_request_and_provenance(monkeypatch, tmp_path):
    config = tmp_path / "models.json"
    profile = ModelProfile(timeout=120, max_output_tokens=2600, temperature=0.35, reasoning="fast")
    save_model_settings(ModelSettings(enabled=True, profiles=[profile]), config)
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(config))
    monkeypatch.setenv("CRIBA_EXTERNAL_MAX_TOKENS", "12345")
    sent = transporte(monkeypatch, [respuesta(propuesta()), respuesta(critica())])
    local = oc.LocalLlamaInterpreter()
    local.gate_report = {"passed": True}  # Admission is covered independently.
    result = local.proponer("colas", IDEA)
    assert result.es_propuesta
    assert local.timeout_s == 120
    for _, payload in sent:
        assert payload["max_tokens"] == 2600
        assert payload["temperature"] == 0.35
        assert payload["reasoning_effort"] == "none"
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert result.provenance.generation_parameters == local.generation_parameters


def test_openrouter_reasoning_is_explicit_and_configuration_is_snapshotted(monkeypatch):
    monkeypatch.setenv("CRIBA_EXTERNAL_MAX_TOKENS", "8192")
    sent = transporte(monkeypatch, [respuesta(propuesta()), respuesta(critica())])
    port = oc.OpenAICompatibleInterpreter(
        base_url="https://openrouter.ai/api/v1", reasoning_effort="none"
    )
    monkeypatch.setenv("CRIBA_EXTERNAL_MAX_TOKENS", "2048")
    assert port.proponer("colas", IDEA).es_propuesta
    assert sent[0][1]["max_tokens"] == 8192
    assert sent[0][1]["reasoning"] == {"effort": "none"}


def test_changed_generation_policy_retries_same_stored_identity(monkeypatch, tmp_path):
    sent = transporte(monkeypatch, [respuesta(propuesta()), respuesta(critica())] * 2)
    storage = Storage(tmp_path / "cache.db")
    for tokens in (4096, 8192):
        port = oc.OpenAICompatibleInterpreter(model="m", max_tokens=tokens)
        judge = JuezInterprete(storage=storage, interpreter=port)
        result = judge.interpretar_lote("colas", [IDEA], "a", "r", 42)
        assert (
            result["interpretados"][0]["interprete_provenance"]["generation_parameters"][
                "max_tokens"
            ]
            == tokens
        )
    assert len(sent) == 4
    row = InterpreteStore(storage).get_verdict(IDEA["id"], "m", run_id="r", seed=42)
    assert row["provenance"]["generation_parameters"]["max_tokens"] == 8192


def test_version_is_distribution_version():
    assert __version__ == version("criba")
    assert Handler.server_version == f"CRIBA/{__version__}"


def test_bad_profile_timeout_and_parallelism_are_bounded():
    profile = ModelProfile.from_dict(json.loads('{"timeout":"NaN","parallel_slots":999}'))
    assert profile.timeout == 300
    assert profile.parallel_slots == 16
