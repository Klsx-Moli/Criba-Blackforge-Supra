"""Tests de regresión para el manejo de tipos en IntelligenceStore.save_documents.

Verifica que campos textuales tupla de un elemento (coma final accidental)
sean detectados con un error claro en lugar de un TypeError de SQLite opaco.
"""
import pytest

from criba.intelligence.storage.store import IntelligenceStore


def test_rejects_tuple_abstract(tmp_path):
    store = IntelligenceStore(tmp_path / "intelligence.sqlite3")

    doc = {
        "doc_id": "doc-bad-abstract",
        "abstract": ("texto accidental en tupla",),
    }

    with pytest.raises(TypeError, match="expected_str_or_none"):
        store.save_document(doc)


def test_accepts_string_abstract(tmp_path):
    store = IntelligenceStore(tmp_path / "intelligence.sqlite3")

    doc = {
        "doc_id": "doc-good-abstract",
        "abstract": "texto válido",
    }

    store.save_document(doc)
    saved = store.get_document("doc-good-abstract")
    assert saved is not None
    assert saved["abstract"] == "texto válido"
