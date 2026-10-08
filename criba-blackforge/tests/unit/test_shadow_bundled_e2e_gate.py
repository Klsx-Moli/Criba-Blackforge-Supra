"""Contract: a Qt startup, stale artifact or synthetic proposal cannot pass M2/M3."""
from copy import deepcopy

import pytest

from scripts.verify_shadow_bundle_journey import summarize


def _image():
    return {"sampled_distinct_colors": 31, "bytes": 16000, "sha256": "a" * 64}


def _valid():
    journey = {
        "status": "BUNDLED_JOURNEY_PASS", "project_id": "astram2a1b2c3d4e5",
        "http_get_status": 200, "artifact_exists": True,
        "receipt_execution_status": "NOT_EXECUTED",
        "receipt_scientific_status": "NOT_VALIDATED",
        "actual_exit_code": 0,
        "image_initial": _image(), "image_generated": _image(),
        "image_supra": _image(),
    }
    restore = {
        "status": "BUNDLED_RESTORE_PASS", "project_id": journey["project_id"],
        "http_get_status": 200, "artifact_exists": True,
        "receipt_execution_status": "NOT_EXECUTED",
        "receipt_scientific_status": "NOT_VALIDATED",
        "actual_exit_code": 0,
        "image_initial": _image(), "image_restored": _image(),
    }
    return journey, restore


def test_two_process_bundle_journey_produces_only_technical_pass():
    a, b = _valid()
    verdict = summarize(a, b)
    assert verdict["status"] == "BUNDLED_E2E_PASS"
    assert verdict["desktop_human_visual_review"] == "NOT_VERIFIED"
    assert verdict["scientific_advantage"] == "NOT_ESTABLISHED"
    assert verdict["external_llm_baseline"] == "NOT_EXECUTED"


@pytest.mark.parametrize("mutation", [
    "first_missing", "second_missing", "id_forged", "http_bad",
    "no_disk", "execution_forged", "science_forged", "image_missing",
    "image_blank", "no_id", "first_crashed", "second_crashed"
])
def test_mutation_cannot_make_bundle_gate_pass(mutation):
    a, b = deepcopy(_valid())
    if mutation == "first_missing":
        a["status"] = "STARTUP_SMOKE_PASS"
    elif mutation == "second_missing":
        b["status"] = "NOT_EXECUTED"
    elif mutation == "id_forged":
        b["project_id"] = "astram2-different"
    elif mutation == "http_bad":
        a["http_get_status"] = 500
    elif mutation == "no_disk":
        b["artifact_exists"] = False
    elif mutation == "execution_forged":
        a["receipt_execution_status"] = "EXECUTED"
    elif mutation == "science_forged":
        b["receipt_scientific_status"] = "VALIDATED"
    elif mutation == "image_missing":
        del b["image_restored"]
    elif mutation == "image_blank":
        a["image_generated"]["sampled_distinct_colors"] = 1
    elif mutation == "no_id":
        a["project_id"] = b["project_id"] = ""
    elif mutation == "first_crashed":
        a["actual_exit_code"] = 3
    elif mutation == "second_crashed":
        b["actual_exit_code"] = 2
    verdict = summarize(a, b)
    assert verdict["status"] == "BUNDLED_E2E_FAIL"
