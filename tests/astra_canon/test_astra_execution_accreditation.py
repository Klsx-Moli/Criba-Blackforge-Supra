"""ASTRA-017/018: declared dossier results are not accredited executions."""

from criba.supra_dossier import (
    guardar_dossier,
    lecciones_previas,
    preparar_dossier,
    registrar_resultado,
)


def dossier():
    return preparar_dossier(
        {
            "candidate_id": "candidate-A",
            "run_id": "run-A",
            "hipotesis": "claim-A",
            "mecanismo": "mechanism-A",
            "mechanism_version": "m-v1",
            "prueba_concreta": "apply intervention A",
            "observable": "metric-A",
            "resultado_favorable_mecanismo": "metric increases",
            "resultado_favorable_alternativa": "metric does not increase",
            "regla_decision": "positive iff metric increases",
        },
        "problem",
        alternativa_explicativa="rival explanation",
    )


def test_astra_017_declared_result_without_execution_identity_is_not_lesson(tmp_path):
    d = dossier()
    guardar_dossier(d, tmp_path)
    result = registrar_resultado(d["dossier_id"], "positivo", directory=tmp_path)
    assert result["accreditation"] == "DECLARED_RESULT"
    assert lecciones_previas("", tmp_path) == []


def test_astra_017_accredited_execution_binds_candidate_mechanism_claim_protocol_and_execution(
    tmp_path,
):
    d = dossier()
    guardar_dossier(d, tmp_path)
    receipt = {
        "candidate_id": d["candidate_id"],
        "mechanism_version": d["mechanism_version"],
        "claim_id": d["claim_id"],
        "protocol_version": d["protocol_version"],
        "execution_id": "exec-1",
        "observed_result": "positivo",
        "result_scope": "EXPERIMENTAL_OBSERVATION",
    }
    result = registrar_resultado(
        d["dossier_id"],
        "positivo",
        directory=tmp_path,
        execution_id="exec-1",
        protocol_version=d["protocol_version"],
        execution_receipt=receipt,
        execution_resolver=lambda execution_id: receipt if execution_id == "exec-1" else None,
    )
    assert result["accreditation"] == "ACCREDITED_EXECUTION"
    assert result["candidate_id"] == "candidate-A"
    assert result["mechanism_version"] == "m-v1"
    assert result["claim_id"]
    assert result["protocol_version"] == d["protocol_version"]
    assert result["execution_id"] == "exec-1"
    assert lecciones_previas("", tmp_path, execution_resolver=lambda _id: receipt)


def test_astra_017_wrong_protocol_cannot_be_accredited_to_dossier(tmp_path):
    d = dossier()
    guardar_dossier(d, tmp_path)
    result = registrar_resultado(
        d["dossier_id"],
        "positivo",
        directory=tmp_path,
        execution_id="exec-1",
        protocol_version="other",
    )
    assert result["accreditation"] == "DECLARED_RESULT"
    assert lecciones_previas("", tmp_path) == []


def test_astra_017_learning_revalidates_receipt_authority_after_restart(tmp_path):
    d = dossier()
    guardar_dossier(d, tmp_path)
    receipt = {
        "candidate_id": d["candidate_id"],
        "mechanism_version": d["mechanism_version"],
        "claim_id": d["claim_id"],
        "protocol_version": d["protocol_version"],
        "execution_id": "exec-restart",
        "observed_result": "positivo",
        "result_scope": "EXPERIMENTAL_OBSERVATION",
    }
    registrar_resultado(
        d["dossier_id"], "positivo", directory=tmp_path,
        execution_id="exec-restart", protocol_version=d["protocol_version"],
        execution_receipt=receipt,
        execution_resolver=lambda execution_id: receipt if execution_id == "exec-restart" else None,
    )
    # Persisted accreditation is historical metadata, not live authority.
    assert lecciones_previas("", tmp_path, execution_resolver=None) == []
    assert lecciones_previas(
        "", tmp_path,
        execution_resolver=lambda execution_id: receipt if execution_id == "exec-restart" else None,
    )
    assert lecciones_previas(
        "", tmp_path,
        execution_resolver=lambda _execution_id: None,
    ) == []


def test_corrupt_parseable_dossier_identity_type_cannot_be_accredited(tmp_path):
    """Persisted dossier identity is authority data; numeric->text coercion must fail closed."""
    d = dossier()
    d["candidate_id"] = 1
    guardar_dossier(d, tmp_path)
    receipt = {
        "candidate_id": "1",
        "mechanism_version": d["mechanism_version"],
        "claim_id": d["claim_id"],
        "protocol_version": d["protocol_version"],
        "execution_id": "exec-type-confusion",
        "observed_result": "positivo",
        "result_scope": "EXPERIMENTAL_OBSERVATION",
    }
    result = registrar_resultado(
        d["dossier_id"], "positivo", directory=tmp_path,
        execution_id="exec-type-confusion", protocol_version=d["protocol_version"],
        execution_resolver=lambda _id: receipt,
    )
    assert result["accreditation"] == "DECLARED_RESULT"
    assert lecciones_previas("", tmp_path, execution_resolver=lambda _id: receipt) == []
