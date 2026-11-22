"""Synthetic gate tests, not LLM evaluations."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pilot_gate as gate


def fixtures(phase="A"):
    refs = gate.references()
    return [{**row, "outcome": refs[row["case_id"]], "physical_calls": 1}
            for row in gate.schedule(phase)]


class PilotGateTests(unittest.TestCase):
    def test_schedule_prefix_and_exact_budgets(self):
        a, b, c = (gate.schedule(p) for p in ("A", "B", "C"))
        self.assertEqual([len(a), len(b), len(c)], [16, 36, 108])
        self.assertEqual(a, b[:16])
        self.assertEqual(b, c[:36])
        for plan in (a, b, c):
            self.assertEqual(len({gate._key(row) for row in plan}), len(plan))
            for i in range(0, len(plan), 2):
                self.assertEqual(plan[i]["case_id"], plan[i + 1]["case_id"])
                self.assertNotEqual(plan[i]["arm"], plan[i + 1]["arm"])
                self.assertEqual(plan[i]["repetition"], plan[i + 1]["repetition"])

    def test_changed_manifest_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(gate.__file__)
            altered = Path(tmp) / "pilot_cases.json"
            altered.write_bytes(source.with_name("pilot_cases.json").read_bytes() + b" ")
            with patch.object(gate, "__file__", str(Path(tmp) / source.name)):
                with self.assertRaises(ValueError):
                    gate.references()

    def test_no_reference_in_schedule(self):
        for row in gate.schedule("C"):
            self.assertEqual(set(row), {"case_id", "repetition", "arm"})

    def test_ideal_result_not_authorization_or_gain(self):
        for phase in ("A", "B", "C"):
            result = gate.summarize(phase, fixtures(phase))
            self.assertEqual(result["status"], "THRESHOLDS_MET_ONLY")
            self.assertEqual(result["gain"], "NO_GAIN_OBSERVED")
            self.assertEqual(result["p0_status"], "OPEN")
            self.assertEqual(result["authorization"], "NOT_GRANTED_BY_THIS_TOOL")

    def test_evident_sample_gain(self):
        rows = fixtures()
        for row in rows:
            if row["arm"] == "S0" and row["outcome"] == "REJECT":
                row["outcome"] = "SUPPORT"
        self.assertEqual(gate.summarize("A", rows)["gain"], "FEWER_FALSE_SUPPORTS_ON_SAMPLE")

    def test_reject_everything_not_a_pass(self):
        rows = fixtures()
        for row in rows:
            if row["arm"] == "S1":
                row["outcome"] = "REJECT"
        self.assertEqual(gate.summarize("A", rows)["status"], "THRESHOLDS_NOT_MET")

    def test_accept_everything_not_a_pass(self):
        rows = fixtures()
        for row in rows:
            if row["arm"] == "S1":
                row["outcome"] = "SUPPORT"
        self.assertEqual(gate.summarize("A", rows)["status"], "THRESHOLDS_NOT_MET")

    def test_each_critical_control(self):
        cases = [("incident", "UNRESOLVED"), ("incident-lexical", "SUPPORT"),
                 ("transfer", "UNRESOLVED"), ("unknown", "REJECT"), ("metric", "SUPPORT")]
        for suffix, replacement in cases:
            with self.subTest(suffix=suffix):
                rows = fixtures()
                target = next(r for r in rows if r["arm"] == "S1"
                              and r["case_id"] == f"CBS500-01-01:{suffix}")
                target["outcome"] = replacement
                self.assertEqual(gate.summarize("A", rows)["status"], "THRESHOLDS_NOT_MET")

    def test_missing_stays_in_denominator(self):
        rows = fixtures()[1:]
        result = gate.summarize("A", rows)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["expected_slots"], 16)
        self.assertEqual(sum(t["NOT_RUN"] for a in result["table"].values()
                             for t in a.values()), 1)

    def test_error_in_either_arm_blocks(self):
        for arm in ("S0", "S1"):
            rows = fixtures()
            next(r for r in rows if r["arm"] == arm)["outcome"] = "ERROR"
            self.assertEqual(gate.summarize("A", rows)["status"], "INCOMPLETE")

    def test_duplicates_and_unscheduled_rows(self):
        rows = fixtures()
        with self.assertRaises(ValueError):
            gate.summarize("A", rows + rows[:1])
        with self.assertRaises(ValueError):
            gate.summarize("A", rows + [{**rows[0], "repetition": 1}])

    def test_invalid_types_and_retry_counts(self):
        for key, values in (("physical_calls", [True, -1, 2, 0, float("nan")]),
                            ("repetition", [False, "0", 1]),
                            ("outcome", ["PASS", "CRITIQUED", None, []])):
            for value in values:
                with self.subTest(key=key, value=value):
                    rows = fixtures()
                    rows[0][key] = value
                    with self.assertRaises(ValueError):
                        gate.summarize("A", rows)

    def test_single_bad_replication_cannot_be_averaged_away(self):
        rows = fixtures("C")
        bad = next(r for r in rows if r["repetition"] == 2 and r["arm"] == "S1"
                   and r["case_id"] == "CBS500-01-01:incident")
        bad["outcome"] = "SUPPORT"
        self.assertEqual(gate.summarize("C", rows)["status"], "THRESHOLDS_NOT_MET")

    def test_later_phase_does_not_erase_failed_stop_go(self):
        rows = fixtures("B")
        target = next(r for r in rows if r["arm"] == "S1"
                      and r["case_id"] == "CBS500-01-01:metric")
        target["outcome"] = "UNRESOLVED"
        result = gate.summarize("B", rows)
        self.assertEqual(result["status"], "THRESHOLDS_NOT_MET")
        self.assertFalse(result["repetitions"][0]["checks"]["reject_minimum"])
        self.assertTrue(result["repetitions"][1]["checks"]["reject_minimum"])

    def test_invalid_container_and_duplicate_json_keys(self):
        for value in ({}, None, "", 5):
            with self.assertRaises(ValueError):
                gate.summarize("A", value)
        for raw in ('{"outcome":"ERROR","outcome":"SUPPORT"}', '[NaN]', '[Infinity]'):
            with self.assertRaises(ValueError):
                gate._strict_load(raw)

    def test_support_loss_visible_even_when_minimum_met(self):
        rows = fixtures()
        target = next(r for r in rows if r["arm"] == "S1"
                      and r["case_id"] == "CBS500-01-01:aligned")
        target["outcome"] = "UNRESOLVED"
        result = gate.summarize("A", rows)
        self.assertEqual(result["status"], "THRESHOLDS_MET_ONLY")
        self.assertEqual(result["support_losses_vs_s0"], [
            {"case_id": "CBS500-01-01:aligned", "repetition": 0}])


if __name__ == "__main__":
    unittest.main()
