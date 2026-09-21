"""Tests de atribución ASTRA: no se reparte evidencia compartida.

Un resultado de un cruce con varios métodos/clases no constituye evidencia
individual para ninguno de sus componentes ni habilita back-off de familia.
"""
from __future__ import annotations

from criba.inventar import record_outcomes
from criba.intelligence.outcome_store import (
    CHANNEL_VERDICT,
    TechniqueOutcomeStore,
)


def _entry_dos_clases() -> dict:
    """Un cruce de dos métodos de clases de pensamiento DISTINTAS."""
    return {
        "candidate_id": "c1",
        "run_id": "run-atrib",
        "classes": ["perspectiva", "ruptura"],
        "method_ids": ["lentes_p_001", "metafora_r_007"],
        "methods": ["Lentes P", "Metafora R"],
        "aportacion_por_tecnica": [],
        "prior_art": {"verdict": "SURVIVED_SEARCH"},
        "judge": {"score": 0.8},
    }


class TestAtribucionPorClase:
    def test_resultado_compartido_no_se_atribuye_a_metodos(self, tmp_path):
        """A shared result is not credited to either component."""
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        sheet = {"run_id": "run-atrib", "entries": [_entry_dos_clases()]}
        record_outcomes(sheet, store, canon_version="c")
        recs = store._read_valid()
        verdicts = {(r["technique_id"], r["family"]) for r in recs
                    if r["channel"] == CHANNEL_VERDICT and r["technique_id"] != "__family__"}
        # A shared candidate result is not individual evidence for either method.
        assert verdicts == set()

    def test_cruce_multiclase_no_crea_agregados_de_familia(self, tmp_path):
        """A multi-family candidate does not fabricate family evidence."""
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        sheet = {"run_id": "run-atrib", "entries": [_entry_dos_clases()]}
        record_outcomes(sheet, store, canon_version="c")
        recs = store._read_valid()
        familias = {r["family"] for r in recs if r["technique_id"] == "__family__"}
        assert familias == set()

    def test_cruce_multiclase_no_expone_prior(self, tmp_path):
        """Neither component receives a prior from shared evidence."""
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        sheet = {"run_id": "run-atrib", "entries": [_entry_dos_clases()]}
        record_outcomes(sheet, store, canon_version="c")
        # la lotería consulta (method_id, thinking_class): ambos deben tener prior
        p1, n1, _ = store.prior(profile="CRIBA", family="perspectiva",
                                technique_id="lentes_p_001", canon_version="c")
        p2, n2, _ = store.prior(profile="CRIBA", family="ruptura",
                                technique_id="metafora_r_007", canon_version="c")
        assert n1 == 0 and p1 == 0.0
        assert n2 == 0 and p2 == 0.0

    def test_tecnicas_tcanon_siguen_registradas(self, tmp_path):
        """Los IDs T-canon del intérprete siguen registrándose (circuito G1)."""
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        entry = _entry_dos_clases()
        entry["aportacion_por_tecnica"] = [{"tecnica": "T059"}]
        sheet = {"run_id": "run-atrib", "entries": [entry]}
        record_outcomes(sheet, store, canon_version="c")
        recs = store._read_valid()
        t_ids = {r["technique_id"] for r in recs if r["channel"] == CHANNEL_VERDICT}
        assert "T059" not in t_ids
