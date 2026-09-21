"""Epistemic contract sentinels for ASTRA-001/003/006/008/014/018/027."""

from criba.bloqueo import FichaBloqueo, validar_ficha
from criba.intelligence.contracts import Claim, EpistemicState, ProvenanceRecord
from criba.intelligence.provenance import ProvenanceValidator
from criba.supra_dossier import preparar_dossier


def test_astra_001_003_unproven_fact_is_downgraded_not_completed():
    claim = Claim(text="unsupported", epistemic_state=EpistemicState.FACT)
    assessment = ProvenanceValidator().assess([claim], [])[0]
    assert claim.epistemic_state is EpistemicState.INFERENCE
    assert not assessment.grounded
    assert "downgraded" in assessment.notes


def test_astra_003_provenance_can_preserve_derivation_version_and_scope():
    provenance = ProvenanceRecord(
        source_id="source-A",
        method="derived",
        transformation="extract-and-normalize-v1",
        source_version="snapshot-2026-09-21",
        scope="claim:C-1",
    )
    payload = provenance.to_dict()
    assert payload["source_id"] == "source-A"
    assert payload["transformation"] == "extract-and-normalize-v1"
    assert payload["source_version"] == "snapshot-2026-09-21"
    assert payload["scope"] == "claim:C-1"


def test_astra_014_bloqueo_preserves_evidence_change_failure_and_origin():
    ficha = FichaBloqueo(
        resultado_buscado="reduce error",
        bloqueo="unknown coupling",
        explicacion_bloqueo="candidate hypothesis",
        origen_bloqueo="hipotesis",
        evidencia=[{"texto": "missing A/B", "origen": "pendiente", "relacion": "falta_comprobar"}],
        cambio_propuesto="isolate the dependency",
        condicion_fallo="no effect under intervention",
    )
    assert validar_ficha(ficha) == []
    record = ficha.to_dict()
    assert record["evidencia"][0]["origen"] == "pendiente"
    assert record["cambio_propuesto"] == "isolate the dependency"
    assert record["condicion_fallo"] == "no effect under intervention"


def test_astra_006_018_prepared_dossier_is_protocol_not_observed_success():
    dossier = preparar_dossier(
        {
            "candidate_id": "C-1",
            "mecanismo": "mechanism",
            "hipotesis": "hypothesis",
            "prueba_concreta": "measure delta",
        },
        "problem",
    )
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    assert dossier["prueba_discriminante"]["afirmacion_decisiva"]
    assert dossier["prueba_discriminante"]["condicion_fracaso"]
    assert dossier["prueba_discriminante"]["estado_prueba"] == "NO_EJECUTADA"
    assert "resultado" not in dossier
    assert "accreditation" not in dossier
