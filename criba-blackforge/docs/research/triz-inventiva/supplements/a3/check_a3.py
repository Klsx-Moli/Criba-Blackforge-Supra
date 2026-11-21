"""Checker exclusivo del sidecar A3. Biblioteca estándar; sin red ni imports CRIBA.
No sustituye validador padre ni valida mecanismos, novedad, seguridad o ciencia.
Uso: python check_a3.py --self-test
     python check_a3.py payload_a3.json
"""
from __future__ import annotations
import copy
import json
import sys
import unittest
from pathlib import Path

SCHEMA = "criba.academic.a3.sidecar/1"
GROUPS = {"sources": "source_id", "claims": "claim_id", "operators": "operator_id", "cards": "card_id", "examples": "example_id"}

def nonempty(x):
    return isinstance(x, str) and bool(x.strip())

def unknown_marker(x):
    if not isinstance(x, str):
        return False
    s = x.strip().upper()
    return s == "UNKNOWN" or s.startswith("UNKNOWN:")

def field_state(obj, key):
    if key not in obj:
        return "ABSENT"
    x = obj[key]
    if x is None:
        return "NULL"
    if isinstance(x, str) and not x.strip():
        return "EMPTY"
    if unknown_marker(x):
        return "UNKNOWN"
    if type(x) in (int, float) and x == 0:
        return "ZERO"
    return "VALUE"

def check_mapping(cross):
    errors = []
    if not isinstance(cross, dict):
        return ["MAP_TYPE"]
    mapping = cross.get("mapping")
    relations = cross.get("matched_relations")
    if not isinstance(mapping, list) or not mapping:
        return ["MAP_MISSING"]
    pairs, targets = {}, set()
    for pair in mapping:
        if not isinstance(pair, dict) or not nonempty(pair.get("source")) or not nonempty(pair.get("target")):
            errors.append("MAP_ITEM_TYPE")
            continue
        s, t = pair["source"], pair["target"]
        if s in pairs or t in targets:
            errors.append("MAP_NOT_ONE_TO_ONE")
        pairs[s] = t
        targets.add(t)
    if not isinstance(relations, list) or not relations:
        return errors + ["RELATIONS_MISSING"]
    for relation in relations:
        if not isinstance(relation, dict):
            errors.append("RELATION_TYPE")
            continue
        a, b = relation.get("source"), relation.get("target")
        if not isinstance(a, dict) or not isinstance(b, dict):
            errors.append("RELATION_TYPE")
            continue
        aa, bb = a.get("arguments"), b.get("arguments")
        if (not nonempty(a.get("predicate")) or a.get("predicate") != b.get("predicate")
            or not isinstance(aa, list) or not isinstance(bb, list) or not aa or len(aa) != len(bb)):
            errors.append("RELATION_SHAPE")
            continue
        for s, t in zip(aa, bb):
            if not nonempty(s) or not nonempty(t) or pairs.get(s) != t:
                errors.append("RELATION_CONNECTIVITY")
    return errors

def check(bundle):
    errors, warnings = [], []
    if not isinstance(bundle, dict):
        return ["BUNDLE_TYPE"], warnings
    if bundle.get("schema_version") != SCHEMA:
        errors.append("SCHEMA_VERSION")
    indexes, rows = {}, {}
    for group, key in GROUPS.items():
        data = bundle.get(group)
        if not isinstance(data, list):
            errors.append(f"{group}:LIST_REQUIRED")
            rows[group], indexes[group] = [], {}
            continue
        rows[group], indexes[group] = data, {}
        for row in data:
            if not isinstance(row, dict):
                errors.append(f"{group}:OBJECT_REQUIRED")
                continue
            rid = row.get(key)
            if not nonempty(rid):
                errors.append(f"{group}:ID_TYPE")
                continue
            if rid in indexes[group]:
                errors.append(f"{group}:DUPLICATE_ID:{rid}")
            else:
                indexes[group][rid] = row
    counts = bundle.get("counts")
    if not isinstance(counts, dict):
        errors.append("COUNTS_TYPE")
    else:
        for group in GROUPS:
            if type(counts.get(group)) is not int or counts[group] != len(rows[group]):
                errors.append(f"{group}:COUNT_MISMATCH")
    def refs(row, field, target, locator, required=True):
        value = row.get(field)
        if not isinstance(value, list) or (required and not value) or any(not nonempty(x) for x in value):
            errors.append(f"{locator}:{field}:LIST_OF_IDS_REQUIRED")
            return
        for rid in value:
            if rid not in indexes[target]:
                errors.append(f"{locator}:{field}:UNKNOWN_REF:{rid}")
    for sid, src in indexes["sources"].items():
        for f in ("title", "url", "reading_level", "locator", "limitations", "reuse_policy"):
            if not nonempty(src.get(f)):
                errors.append(f"{sid}:MISSING:{f}")
        if src.get("license_status") == "NOT_VERIFIED":
            warnings.append(f"{sid}:RIGHTS_UNVERIFIED_NO_ORIGINAL_REDISTRIBUTION")
        if src.get("year") is not None and (type(src["year"]) is not int or src["year"] < 1):
            errors.append(f"{sid}:YEAR_TYPE")
    for group in ("claims", "operators"):
        for rid, row in indexes[group].items():
            refs(row, "source_ids", "sources", rid)
    for rid, op in indexes["operators"].items():
        for f in ("appropriate_when", "original_example", "counterexample", "rival_explanation", "discriminating_test", "extension_of"):
            if not nonempty(op.get(f)):
                errors.append(f"{rid}:MISSING:{f}")
        for f in ("required_inputs", "transformation_steps", "required_outputs", "preconditions", "hard_invariants", "abstention_or_failure"):
            v = op.get(f)
            if not isinstance(v, list) or not v or any(not nonempty(x) for x in v):
                errors.append(f"{rid}:LIST_REQUIRED:{f}")
    graph = {}
    for rid, card in indexes["cards"].items():
        refs(card, "depends_on", "cards", rid, required=False)
        deps = card.get("depends_on")
        graph[rid] = [d for d in deps if nonempty(d) and d in indexes["cards"]] if isinstance(deps, list) else []
    visiting, done = set(), set()
    def visit(rid):
        if rid in visiting:
            errors.append("CARD_CYCLE")
            return
        if rid in done:
            return
        visiting.add(rid)
        for dep in graph.get(rid, []):
            visit(dep)
        visiting.remove(rid)
        done.add(rid)
    for rid in graph:
        visit(rid)
    for rid, ex in indexes["examples"].items():
        if ex.get("data_class") != "SYNTHETIC_ORIGINAL_FIXTURE":
            errors.append(f"{rid}:FIXTURE_LABEL")
        refs(ex, "operator_ids", "operators", rid)
        if "cross_domain" in ex:
            errors += [f"{rid}:{e}" for e in check_mapping(ex["cross_domain"])]
        if "provenance" in ex:
            p = ex["provenance"]
            if not isinstance(p, dict) or type(p.get("seed_present")) is not bool:
                errors.append(f"{rid}:SEED_PRESENCE_TYPE")
            elif p["seed_present"]:
                if "seed" not in p or type(p["seed"]) is not int:
                    errors.append(f"{rid}:SEED_TYPE")
            elif "seed" in p:
                errors.append(f"{rid}:SEED_CONTRADICTION")
    for group in ("operators", "cards", "examples"):
        for rid, row in indexes[group].items():
            if group == "examples" and "states" in row:
                st = row["states"]
                if not isinstance(st, dict) or st.get("execution") != "NOT_EXECUTED" or st.get("scientific_validation") != "NOT_VALIDATED_FOR_CRIBA":
                    errors.append(f"{rid}:STATE_PROMOTION")
            elif row.get("execution_status") != "NOT_EXECUTED" or row.get("scientific_status") != "NOT_VALIDATED_FOR_CRIBA":
                errors.append(f"{rid}:STATE_PROMOTION")
    return errors, warnings

def sample():
    return {"schema_version": SCHEMA, "sources": [{"source_id":"s1", "title":"original fixture", "url":"urn:fixture:s1", "reading_level":"FIXTURE", "locator":"fixture", "limitations":"not evidence", "reuse_policy":"original", "license_status":"NOT_VERIFIED", "year":None}],
    "claims": [{"claim_id":"c1", "source_ids":["s1"]}],
    "operators": [{"operator_id":"o1", "source_ids":["s1"], **{k:"fixture" for k in ("appropriate_when","original_example","counterexample","rival_explanation","discriminating_test","extension_of")}, **{k:["fixture"] for k in ("required_inputs","transformation_steps","required_outputs","preconditions","hard_invariants","abstention_or_failure")}, "execution_status":"NOT_EXECUTED", "scientific_status":"NOT_VALIDATED_FOR_CRIBA"}],
    "cards": [{"card_id":"t1","depends_on":["t2"],"execution_status":"NOT_EXECUTED","scientific_status":"NOT_VALIDATED_FOR_CRIBA"},{"card_id":"t2","depends_on":[],"execution_status":"NOT_EXECUTED","scientific_status":"NOT_VALIDATED_FOR_CRIBA"}],
    "examples": [{"example_id":"e1","data_class":"SYNTHETIC_ORIGINAL_FIXTURE","operator_ids":["o1"],"provenance":{"seed_present":False},"execution_status":"NOT_EXECUTED","scientific_status":"NOT_VALIDATED_FOR_CRIBA"}],
    "counts":{"sources":1,"claims":1,"operators":1,"cards":2,"examples":1}}

class Tests(unittest.TestCase):
    def setUp(self): self.b = sample()
    def errors(self): return check(self.b)[0]
    def test_valid_forward_dependency(self): self.assertEqual(self.errors(), [])
    def test_order_invariance(self):
        a = self.errors(); self.b["cards"].reverse(); self.assertEqual(self.errors(), a)
    def test_duplicate_card(self):
        self.b["cards"].append(copy.deepcopy(self.b["cards"][0])); self.assertTrue(any("DUPLICATE_ID" in x for x in self.errors()))
    def test_duplicate_source(self):
        self.b["sources"].append(copy.deepcopy(self.b["sources"][0])); self.assertTrue(any("DUPLICATE_ID" in x for x in self.errors()))
    def test_missing_dependency(self):
        self.b["cards"][0]["depends_on"] = ["absent"]; self.assertTrue(any("UNKNOWN_REF" in x for x in self.errors()))
    def test_dependency_type(self):
        self.b["cards"][0]["depends_on"] = "t2"; self.assertTrue(self.errors())
    def test_unhashable_dependency(self):
        self.b["cards"][0]["depends_on"] = [{}]; self.assertTrue(self.errors())
    def test_unhashable_id(self):
        self.b["cards"][0]["card_id"] = []; self.assertTrue(self.errors())
    def test_cycle(self):
        self.b["cards"][1]["depends_on"] = ["t1"]; self.assertIn("CARD_CYCLE", self.errors())
    def test_missing_source_ref(self):
        self.b["operators"][0]["source_ids"] = ["absent"]; self.assertTrue(any("UNKNOWN_REF" in x for x in self.errors()))
    def test_unverified_license_is_warning(self):
        e,w = check(self.b); self.assertEqual(e, []); self.assertTrue(w)
    def test_unknown_delimiter(self):
        self.assertTrue(unknown_marker(" UNKNOWN: explicación ")); self.assertTrue(unknown_marker("UNKNOWN")); self.assertFalse(unknown_marker("UNKNOWNLAND"))
    def test_field_states_distinct(self):
        vals=[field_state({},"x")]+[field_state({"x":v},"x") for v in (None,"",0,"UNKNOWN",False)]
        self.assertEqual(vals,["ABSENT","NULL","EMPTY","ZERO","UNKNOWN","VALUE"])
    def test_seed_zero(self):
        self.b["examples"][0]["provenance"]={"seed_present":True,"seed":0}; self.assertEqual(self.errors(), [])
    def test_seed_false_not_zero(self):
        self.b["examples"][0]["provenance"]={"seed_present":True,"seed":False}; self.assertTrue(self.errors())
    def test_seed_contradiction(self):
        self.b["examples"][0]["provenance"]={"seed_present":False,"seed":0}; self.assertTrue(self.errors())
    def test_state_promotion(self):
        self.b["operators"][0]["execution_status"]="EXECUTED"; self.assertTrue(any("STATE_PROMOTION" in x for x in self.errors()))
    def test_schema_version(self):
        self.b["schema_version"]="future"; self.assertIn("SCHEMA_VERSION",self.errors())
    def test_counterexample_required(self):
        del self.b["operators"][0]["counterexample"]; self.assertTrue(self.errors())
    def test_mapping_consistency(self):
        x={"mapping":[{"source":"a","target":"x"},{"source":"b","target":"y"}],"matched_relations":[{"source":{"predicate":"r","arguments":["a","b"]},"target":{"predicate":"r","arguments":["x","y"]}}]}
        self.assertEqual(check_mapping(x),[])
        x["matched_relations"][0]["target"]["arguments"].reverse()
        self.assertIn("RELATION_CONNECTIVITY",check_mapping(x))
    def test_mapping_target_duplicate(self):
        x={"mapping":[{"source":"a","target":"x"},{"source":"b","target":"x"}],"matched_relations":[]}
        self.assertIn("MAP_NOT_ONE_TO_ONE",check_mapping(x))
    def test_counts(self):
        self.b["counts"]["sources"]=True; self.assertTrue(any("COUNT_MISMATCH" in x for x in self.errors()))
    def test_malformed_root(self): self.assertEqual(check([])[0],["BUNDLE_TYPE"])
    def test_fixture_label(self):
        self.b["examples"][0]["data_class"]="OBSERVED"; self.assertTrue(any("FIXTURE_LABEL" in x for x in self.errors()))

def reject_duplicates(pairs):
    obj = {}
    for k,v in pairs:
        if k in obj:
            raise ValueError("JSON_DUPLICATE_KEY:" + k)
        obj[k] = v
    return obj

def reject_constant(x):
    raise ValueError("JSON_NONFINITE:" + x)

def main(argv):
    if argv == ["--self-test"]:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    if len(argv) != 1:
        print("Usage: python check_a3.py --self-test | payload_a3.json", file=sys.stderr)
        return 2
    try:
        data=json.loads(Path(argv[0]).read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates, parse_constant=reject_constant)
        e,w=check(data)
    except (OSError,ValueError,RecursionError) as exc:
        print(json.dumps({"load_error":str(exc)},ensure_ascii=False)); return 2
    print(json.dumps({"errors":e,"warnings":w,"scope":"STRUCTURAL_A3_ONLY_NOT_PRODUCT_NOT_SCIENCE"},ensure_ascii=False,indent=2))
    return 1 if e else 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
