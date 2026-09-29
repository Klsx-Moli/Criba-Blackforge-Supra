"""ASTRA manifest schema and authority sentinels (ASTRA-001..035)."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "governance" / "ASTRA_CANON.yaml"
VALID_STATUSES = {"CANON", "CANON_WITH_LIMITATIONS", "RESEARCH_ONLY"}


def _manifest():
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def test_astra_034_manifest_contains_exactly_35_ordered_contracts():
    data = _manifest()
    contracts = data["contracts"]
    assert [c["id"] for c in contracts] == [f"ASTRA-{i:03d}" for i in range(1, 36)]
    assert len({c["id"] for c in contracts}) == 35


def test_astra_034_every_contract_is_machine_readable_and_mapped():
    for item in _manifest()["contracts"]:
        assert item["name"]
        assert item["status"] in VALID_STATUSES
        assert item["scopes"]
        assert item["contract"]
        assert item["implementation"]
        assert item["tests"]
        assert all((ROOT / path).exists() for path in item["implementation"])
        assert all((ROOT / path).exists() for path in item["tests"])
        assert "limitations" in item


def test_astra_025_035_research_only_is_not_promoted():
    by_id = {c["id"]: c for c in _manifest()["contracts"]}
    assert by_id["ASTRA-025"]["status"] == "RESEARCH_ONLY"
    assert by_id["ASTRA-035"]["status"] == "RESEARCH_ONLY"
    state = _manifest()["scientific_state"]
    assert state["D3_NOVELTY"] == "UNRESOLVED"
    assert state["D4_FUNCTIONAL_DIVERSITY"] == "UNRESOLVED"
    assert state["D6_ADAPTIVE_BENEFIT"] == "STILL_UNRESOLVED"
    assert state["SCIENTIFIC_ADVANTAGE_OF_CRIBA"] == "NOT_ESTABLISHED"


def test_astra_032_anti_goodhart_is_contract_only_in_this_mission():
    data = _manifest()
    assert data["scientific_state"]["ANTI_GOODHART_RUNTIME"].endswith("NOT_IMPLEMENTED")
    prohibited = [
        ROOT / "src" / "criba" / "anti_goodhart.py",
        ROOT / "src" / "criba" / "anti_goodhart_runtime.py",
    ]
    assert not any(path.exists() for path in prohibited)


def test_astra_013_027_028_do_not_claim_unimplemented_scientific_capability():
    by_id = {c["id"]: c for c in _manifest()["contracts"]}
    limitations_013 = " ".join(by_id["ASTRA-013"]["limitations"]).casefold()
    limitations_027 = " ".join(by_id["ASTRA-027"]["limitations"]).casefold()
    limitations_028 = " ".join(by_id["ASTRA-028"]["limitations"]).casefold()
    assert "no se emite" in limitations_013
    assert "no ejecuta campañas" in limitations_027
    assert "no satisfacen" in limitations_028


def test_astra_032_entry_gate_requires_g1_to_g4_before_standard_activation():
    gate = _manifest()["anti_goodhart_entry_gate"]
    assert gate["decision"] == "ASTRA_BASE_READY_AFTER_LISTED_FIXES"
    assert gate["activation_rule"] == "STANDARD_MUST_REMAIN_DISABLED_UNTIL_G1_G4_VERIFIED"
    for key in (
        "G1_BASE_COMMON",
        "G2_EFFECT_SEPARATION",
        "G3_TEMPORAL_NONINTERFERENCE",
        "G4_TRAJECTORY_VERIFICATION",
    ):
        assert gate[key]
    assert any("shared RNG" in rule for rule in gate["G2_EFFECT_SEPARATION"])
    assert any("after restart" in rule for rule in gate["G4_TRAJECTORY_VERIFICATION"])


def test_astra_025_off_policy_stays_research_only_and_opt_in():
    manifest = _manifest()
    by_id = {c["id"]: c for c in manifest["contracts"]}
    assert by_id["ASTRA-025"]["status"] == "RESEARCH_ONLY"

    off_policy = (ROOT / "src" / "criba" / "intelligence" / "off_policy.py").read_text(
        encoding="utf-8"
    )
    lottery = (ROOT / "src" / "criba" / "lottery.py").read_text(encoding="utf-8")
    assert "RESEARCH_ONLY = True" in off_policy
    assert "off_policy_logging: bool = False" in lottery
    assert "reward=None" in lottery
