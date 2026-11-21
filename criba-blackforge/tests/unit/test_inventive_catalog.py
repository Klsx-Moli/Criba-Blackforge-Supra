"""The shipped catalog must expose original operational records, not names alone."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from criba.catalog import methods
from criba.interprete.contrato import prompt_propuesta
from criba.inventar import invent
from criba.storage import Storage
from criba.supra_dossier import preparar_dossier

ROOT = Path(__file__).resolve().parents[2]
MATERIAL = ROOT / "docs/research/triz-inventiva"


def test_all_parent_a3_a4_operators_are_shipped_without_semantic_loss():
    originals = [
        json.loads(line)
        for line in (MATERIAL / "operators/operators.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    for name in ("a3", "a4"):
        payload = json.loads(
            (MATERIAL / f"supplements/{name}/payload_{name}.json").read_text(encoding="utf-8")
        )
        originals.extend(payload["operators"])
    catalog = {record["id"]: record for record in methods()}
    missing = [
        record["operator_id"] for record in originals if record["operator_id"] not in catalog
    ]
    assert missing == [], f"Operaciones preparadas pero ausentes del catálogo real: {missing}"
    assert len(originals) == len({record["operator_id"] for record in originals})
    for original in originals:
        runtime = catalog[original["operator_id"]]
        assert runtime["operator_record"] == original
        assert runtime["thinking_class"] in {"perspectiva", "generacion", "ruptura", "escape"}
        assert {s["source_id"] for s in runtime["source_records"]} == set(original["source_ids"])
        for step in original.get("transformation_steps", [original.get("transformation", "")]):
            assert step and step in runtime["description"]


@pytest.mark.parametrize(
    "operator_id", [record["id"] for record in methods() if "operator_record" in record]
)
def test_selected_operation_survives_model_input_and_durable_output(tmp_path, operator_id):
    catalog = {record["id"]: record for record in methods()}
    lens = next(
        record
        for record in catalog.values()
        if record.get("thinking_class") == "perspectiva" and "operator_record" not in record
    )
    selected = [catalog[operator_id], lens]
    delivered = []

    def synthetic_proposer(query, idea, domain, evidence):
        decoded = json.loads(
            prompt_propuesta(query, idea, domain, evidence).split("\nDATOS:\n", 1)[1]
        )["CRUCE"]
        delivered.append(decoded["cross_operational_records"])
        return {
            "estado": "PROPUESTA",
            "hipotesis": "Hipótesis sintética sin modelo",
            "mecanismo": "Mecanismo sintético usado exclusivamente para verificar el transporte.",
            "interpretacion_model_requests": 0,
        }

    sheet = invent(
        "Prueba sintética del transporte",
        seed=42,
        rounds=1,
        batch_size=2,
        top=1,
        methods=selected,
        sources=[],
        offline=True,
        history_storage=False,
        proponer=synthetic_proposer,
    )
    assert delivered, "el consumidor debe haber recibido un cruce"
    by_id = {record["id"]: record for record in delivered[0]}
    assert {record["id"] for record in selected} == set(by_id)
    for original in selected:
        transported = by_id[original["id"]]
        assert {key: transported[key] for key in original} == original
    assert sheet["entries"][0]["cross_operational_records"] == delivered[0]
    db = tmp_path / "preservation.sqlite3"
    ident = Storage(db).save_invention(sheet)
    restored = Storage(db).get(ident)["packet"]["sheet"]["entries"][0]
    assert restored["cross_operational_records"] == delivered[0]


def test_dossier_preserves_operations_in_existing_provenance_envelope():
    records = [record for record in methods() if record["id"] in {"A3-OP-GEN-01", "A4-OP-MOR-01"}]
    entry = {
        "candidate_id": "synthetic-no-model",
        "hipotesis": "Hipótesis sintética",
        "mecanismo": "Mecanismo exclusivamente sintético para comprobar conservación de datos.",
        "cross_operational_records": records,
        "interpretacion_provenance": {},
    }
    dossier = preparar_dossier(entry, "Problema sintético")
    assert dossier["interpretacion"]["provenance"]["cross_operational_records"] == records
