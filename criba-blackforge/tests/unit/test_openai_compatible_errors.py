"""Tests unitarios para el manejo de errores del intérprete externo.

Verifica que content=None, contenido vacío y tipos inválidos producen
errores diagnosticables (ExternalModelEmptyResponse) en lugar de TypeError
op silenciamiento.
"""
import pytest

from criba.interprete.openai_compatible import (
    ExternalModelEmptyResponse,
    _extract_content,
    _parse_model_json,
)


def test_null_content_is_diagnostic():
    with pytest.raises(ExternalModelEmptyResponse, match="external_model_null_content"):
        _extract_content({
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": None},
            }]
        })


def test_null_content_with_length_is_diagnostic():
    with pytest.raises(ExternalModelEmptyResponse, match="length"):
        _extract_content({
            "choices": [{
                "finish_reason": "length",
                "message": {"content": None},
            }]
        })


def test_empty_content_is_diagnostic():
    with pytest.raises(ExternalModelEmptyResponse, match="empty_content"):
        _extract_content({
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": "   "},
            }]
        })


def test_no_choices_is_diagnostic():
    with pytest.raises(ExternalModelEmptyResponse, match="empty_choices"):
        _extract_content({"choices": []})


def test_valid_content_is_extracted():
    result = _extract_content({
        "choices": [{
            "finish_reason": "stop",
            "message": {"content": '{"decision":"propose"}'},
        }]
    })
    assert result == '{"decision":"propose"}'


def test_parse_model_json_valid():
    parsed = _parse_model_json('{"decision":"propose"}')
    assert parsed == {"decision": "propose"}


def test_parse_model_json_invalid():
    from criba.interprete.openai_compatible import ExternalModelInvalidJSON
    with pytest.raises(ExternalModelInvalidJSON, match="external_model_invalid_json"):
        _parse_model_json("not json")


def test_parse_model_json_not_object():
    from criba.interprete.openai_compatible import ExternalModelInvalidJSON
    with pytest.raises(ExternalModelInvalidJSON, match="invalid_json_type"):
        _parse_model_json("[1, 2, 3]")
