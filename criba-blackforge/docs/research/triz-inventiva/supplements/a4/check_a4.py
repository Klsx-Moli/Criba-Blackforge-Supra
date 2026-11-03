"""Checker exclusivo del sidecar A4. Biblioteca estandar; sin red ni imports CRIBA.
No valida ciencia, novedad, seguridad ni utilidad. Uso:
  python check_a4.py --self-test
  python check_a4.py payload_a4.json
"""
from __future__ import annotations
import copy, itertools, json, sys, unittest
from pathlib import Path

SCHEMA = "criba.academic.a4.sidecar/1"
GROUPS = {"sources": "source_id", "claims": "claim_id", "operators": "operator_id", "cards": "card_id", "examples": "example_id"}

def nonempty(x):
    return isinstance(x, str) and bool(x.strip())

def unknown_marker(x):
    if not isinstance(x, str):
        return False
    s = x.strip().upper()
    return s == "UNKNOWN" or s.startswith("UNKNOWN:")

def check_morph(m):
    """Caja morfologica: parametros con valores, pares incompatibles validos, espacio formal y consistente."""
    errs = []
    if not isinstance(m, dict) or not isinstance(m.get("parameters"), dict) or not m["parameters"]:
        return ["MORPH_PARAMETERS"], None
    params = m["parameters"]
    for p, vals in params.items():
        if not nonempty(p) or not isinstance(vals, list) or not vals or any(not nonempty(v) for v in vals) or len(set(vals)) != len(vals):
            errs.append("MORPH_VALUES:" + str(p))
    if errs:
        return errs, None
    pairs = m.get("incompatible_pairs", [])
    if not isinstance(pairs, list):
        return ["MORPH_PAIRS_TYPE"], None
    norm = []
    for pr in pairs:
        ok = (isinstance(pr, list) and len(pr) == 2 and all(isinstance(x, list) and len(x) == 2 and all(nonempty(y) for y in x) for x in pr))
        if not ok:
            errs.append("MORPH_PAIR_SHAPE"); continue
        (p1, v1), (p2, v2) = pr
        if p1 == p2:
            errs.append("MORPH_PAIR_SAME_PARAMETER"); continue
        if p1 not in params or p2 not in params or v1 not in params[p1] or v2 not in params[p2]:
            errs.append("MORPH_PAIR_UNKNOWN_VALUE"); continue
        norm.append(frozenset({(p1, v1), (p2, v2)}))
    if errs:
        return errs, None
    names = list(params)
    total = consistent = 0
    for combo in itertools.product(*[params[n] for n in names]):
        total += 1
        cells = set(zip(names, combo))
        if not any(pr <= cells for pr in norm):
            consistent += 1
    return [], {"formal": total, "consistent": consistent}

def check_ck(ck):
    errs = []
    if not isinstance(ck, dict):
        return ["CK_TYPE"]
    c, k, part = ck.get("concept"), ck.get("knowledge"), ck.get("partition")
    if not isinstance(c, dict) or c.get("status") != "UNDECIDABLE":
        errs.append("CK_CONCEPT_MUST_BE_UNDECIDABLE")
    if not isinstance(k, list) or not k:
        errs.append("CK_KNOWLEDGE_MISSING")
    else:
        for item in k:
            if not isinstance(item, dict) or item.get("truth") not in ("TRUE", "FALSE") or not nonempty(item.get("source")):
                errs.append("CK_KNOWLEDGE_ITEM")
    if not isinstance(part, dict) or part.get("type") not in ("RESTRICTIVE", "EXPANSIVE") or not nonempty(part.get("reason")):
        errs.append("CK_PARTITION")
    return errs

def check_fbs(f):
    errs = []
    if not isinstance(f, dict):
        return ["FBS_TYPE"]
    for key in ("function", "structure", "behaviour_expected", "behaviour_actual"):
        if not nonempty(f.get(key)):
            errs.append("FBS_MISSING:" + key)
    if not errs and f["behaviour_actual"] == f["behaviour_expected"]:
        errs.append("FBS_ACTUAL_COPIES_EXPECTED")
    return errs

def check(bundle):
    errors, warnings = [], []
    if not isinstance(bundle, dict):
        return ["BUNDLE_TYPE"], warnings
    if bundle.get("schema_version") != SCHEMA:
        errors.append("SCHEMA_VERSION")
    idx, rows = {}, {}
    for g, key in GROUPS.items():
        data = bundle.get(g)
        if not isinstance(data, list):
            errors.append(g + ":LIST_REQUIRED"); rows[g] = []; idx[g] = {}; continue
        rows[g], idx[g] = data, {}
        for r in data:
            if not isinstance(r, dict):
                errors.append(g + ":OBJECT_REQUIRED"); continue
            rid = r.get(key)
            if not nonempty(rid):
                errors.append(g + ":ID_TYPE"); continue
            if rid in idx[g]:
                errors.append(f"{g}:DUPLICATE_ID:{rid}")
            else:
                idx[g][rid] = r
    counts = bundle.get("counts")
    if not isinstance(counts, dict):
        errors.append("COUNTS_TYPE")
    else:
        for g in GROUPS:
            if type(counts.get(g)) is not int or counts[g] != len(rows[g]):
                errors.append(g + ":COUNT_MISMATCH")
    def refs(row, field, target, loc, required=True):
        v = row.get(field)
        if not isinstance(v, list) or (required and not v) or any(not nonempty(x) for x in v):
            errors.append(f"{loc}:{field}:LIST_OF_IDS_REQUIRED"); return
        for x in v:
            if x not in idx[target]:
                errors.append(f"{loc}:{field}:UNKNOWN_REF:{x}")
    for sid, s in idx["sources"].items():
        for f in ("title", "url", "reading_level", "locator", "limitations", "reuse_policy"):
            if not nonempty(s.get(f)):
                errors.append(f"{sid}:MISSING:{f}")
        if s.get("license_status") == "NOT_VERIFIED":
            warnings.append(sid + ":RIGHTS_UNVERIFIED")
        y = s.get("year")
        if y is not None and (type(y) is not int or y < 1):
            errors.append(sid + ":YEAR_TYPE")
    for g in ("claims", "operators"):
        for rid, r in idx[g].items():
            refs(r, "source_ids", "sources", rid)
    for rid, o in idx["operators"].items():
        for f in ("appropriate_when", "original_example", "counterexample", "rival_explanation", "discriminating_test", "extension_of"):
            if not nonempty(o.get(f)):
                errors.append(f"{rid}:MISSING:{f}")
        for f in ("required_inputs", "transformation_steps", "required_outputs", "preconditions", "hard_invariants", "abstention_or_failure"):
            v = o.get(f)
            if not isinstance(v, list) or not v or any(not nonempty(x) for x in v):
                errors.append(f"{rid}:LIST_REQUIRED:{f}")
    graph = {}
    for rid, c in idx["cards"].items():
        refs(c, "depends_on", "cards", rid, required=False)
        d = c.get("depends_on")
        graph[rid] = [x for x in d if nonempty(x) and x in idx["cards"]] if isinstance(d, list) else []
    state, done = set(), set()
    def visit(r):
        if r in state:
            errors.append("CARD_CYCLE"); return
        if r in done:
            return
        state.add(r)
        for d in graph.get(r, []):
            visit(d)
        state.discard(r); done.add(r)
    for r in graph:
        visit(r)
    for rid, ex in idx["examples"].items():
        if ex.get("data_class") != "SYNTHETIC_ORIGINAL_FIXTURE":
            errors.append(rid + ":FIXTURE_LABEL")
        refs(ex, "operator_ids", "operators", rid)
        if "morph" in ex:
            e, _ = check_morph(ex["morph"]); errors += [f"{rid}:{x}" for x in e]
        if "ck" in ex:
            errors += [f"{rid}:{x}" for x in check_ck(ex["ck"])]
        if "fbs" in ex:
            errors += [f"{rid}:{x}" for x in check_fbs(ex["fbs"])]
        st = ex.get("states")
        if not isinstance(st, dict) or st.get("execution") != "NOT_EXECUTED" or st.get("scientific_validation") != "NOT_VALIDATED_FOR_CRIBA":
            errors.append(rid + ":STATE_PROMOTION")
    for g in ("operators", "cards"):
        for rid, r in idx[g].items():
            if r.get("execution_status") != "NOT_EXECUTED" or r.get("scientific_status") != "NOT_VALIDATED_FOR_CRIBA":
                errors.append(rid + ":STATE_PROMOTION")
    return errors, warnings

def sample():
    op = {"operator_id": "o1", "source_ids": ["s1"], **{k: "x" for k in ("appropriate_when", "original_example", "counterexample", "rival_explanation", "discriminating_test", "extension_of")}, **{k: ["x"] for k in ("required_inputs", "transformation_steps", "required_outputs", "preconditions", "hard_invariants", "abstention_or_failure")}, "execution_status": "NOT_EXECUTED", "scientific_status": "NOT_VALIDATED_FOR_CRIBA"}
    st = {"execution": "NOT_EXECUTED", "scientific_validation": "NOT_VALIDATED_FOR_CRIBA"}
    return {"schema_version": SCHEMA,
        "sources": [{"source_id": "s1", "title": "t", "url": "u", "reading_level": "r", "locator": "l", "limitations": "l", "reuse_policy": "p", "license_status": "NOT_VERIFIED", "year": None}],
        "claims": [{"claim_id": "c1", "source_ids": ["s1"]}], "operators": [op],
        "cards": [{"card_id": "t1", "depends_on": ["t2"], "execution_status": "NOT_EXECUTED", "scientific_status": "NOT_VALIDATED_FOR_CRIBA"}, {"card_id": "t2", "depends_on": [], "execution_status": "NOT_EXECUTED", "scientific_status": "NOT_VALIDATED_FOR_CRIBA"}],
        "examples": [{"example_id": "e1", "data_class": "SYNTHETIC_ORIGINAL_FIXTURE", "operator_ids": ["o1"], "states": st,
            "morph": {"parameters": {"a": ["1", "2"], "b": ["x", "y"]}, "incompatible_pairs": [[["a", "1"], ["b", "x"]]]},
            "ck": {"concept": {"status": "UNDECIDABLE"}, "knowledge": [{"truth": "TRUE", "source": "FIXTURE"}], "partition": {"type": "RESTRICTIVE", "reason": "r"}},
            "fbs": {"function": "f", "structure": "s", "behaviour_expected": "e", "behaviour_actual": "UNKNOWN"}}],
        "counts": {"sources": 1, "claims": 1, "operators": 1, "cards": 2, "examples": 1}}

class Tests(unittest.TestCase):
    def setUp(self): self.b = sample()
    def err(self): return check(self.b)[0]
    def test_valid(self): self.assertEqual(self.err(), [])
    def test_order(self):
        a = self.err(); self.b["cards"].reverse(); self.assertEqual(self.err(), a)
    def test_dup_card(self):
        self.b["cards"].append(copy.deepcopy(self.b["cards"][0])); self.assertTrue(any("DUPLICATE_ID" in x for x in self.err()))
    def test_dup_source(self):
        self.b["sources"].append(copy.deepcopy(self.b["sources"][0])); self.assertTrue(any("DUPLICATE_ID" in x for x in self.err()))
    def test_missing_dep(self):
        self.b["cards"][0]["depends_on"] = ["zz"]; self.assertTrue(any("UNKNOWN_REF" in x for x in self.err()))
    def test_unhashable_dep(self):
        self.b["cards"][0]["depends_on"] = [{}]; self.assertTrue(self.err())
    def test_unhashable_id(self):
        self.b["cards"][0]["card_id"] = []; self.assertTrue(self.err())
    def test_cycle(self):
        self.b["cards"][1]["depends_on"] = ["t1"]; self.assertIn("CARD_CYCLE", self.err())
    def test_bad_source_ref(self):
        self.b["operators"][0]["source_ids"] = ["zz"]; self.assertTrue(any("UNKNOWN_REF" in x for x in self.err()))
    def test_warning_not_error(self):
        e, w = check(self.b); self.assertEqual(e, []); self.assertTrue(w)
    def test_unknown_marker(self):
        self.assertTrue(unknown_marker(" UNKNOWN: razon ")); self.assertFalse(unknown_marker("UNKNOWNLAND"))
    def test_state_promotion(self):
        self.b["operators"][0]["execution_status"] = "EXECUTED"; self.assertTrue(any("STATE_PROMOTION" in x for x in self.err()))
    def test_example_state_promotion(self):
        self.b["examples"][0]["states"]["execution"] = "EXECUTED"; self.assertTrue(any("STATE_PROMOTION" in x for x in self.err()))
    def test_counterexample_required(self):
        del self.b["operators"][0]["counterexample"]; self.assertTrue(self.err())
    def test_counts_bool(self):
        self.b["counts"]["sources"] = True; self.assertTrue(any("COUNT_MISMATCH" in x for x in self.err()))
    def test_schema(self):
        self.b["schema_version"] = "x"; self.assertIn("SCHEMA_VERSION", self.err())
    def test_root(self): self.assertEqual(check([])[0], ["BUNDLE_TYPE"])
    def test_fixture_label(self):
        self.b["examples"][0]["data_class"] = "OBSERVED"; self.assertTrue(any("FIXTURE_LABEL" in x for x in self.err()))
    def test_morph_counts(self):
        e, r = check_morph(self.b["examples"][0]["morph"]); self.assertEqual((e, r), ([], {"formal": 4, "consistent": 3}))
    def test_morph_unknown_value(self):
        m = copy.deepcopy(self.b["examples"][0]["morph"]); m["incompatible_pairs"][0][0][1] = "9"; self.assertIn("MORPH_PAIR_UNKNOWN_VALUE", check_morph(m)[0])
    def test_morph_same_param(self):
        m = copy.deepcopy(self.b["examples"][0]["morph"]); m["incompatible_pairs"] = [[["a", "1"], ["a", "2"]]]; self.assertIn("MORPH_PAIR_SAME_PARAMETER", check_morph(m)[0])
    def test_morph_duplicate_values(self):
        m = {"parameters": {"a": ["1", "1"]}}; self.assertTrue(check_morph(m)[0])
    def test_morph_order_invariant(self):
        m = copy.deepcopy(self.b["examples"][0]["morph"]); r1 = check_morph(m)[1]
        m["parameters"] = dict(reversed(list(m["parameters"].items()))); self.assertEqual(check_morph(m)[1], r1)
    def test_ck_concept_decidable_rejected(self):
        c = copy.deepcopy(self.b["examples"][0]["ck"]); c["concept"]["status"] = "TRUE"; self.assertIn("CK_CONCEPT_MUST_BE_UNDECIDABLE", check_ck(c))
    def test_ck_knowledge_needs_source(self):
        c = copy.deepcopy(self.b["examples"][0]["ck"]); c["knowledge"][0]["source"] = ""; self.assertIn("CK_KNOWLEDGE_ITEM", check_ck(c))
    def test_ck_knowledge_unknown_truth_rejected(self):
        c = copy.deepcopy(self.b["examples"][0]["ck"]); c["knowledge"][0]["truth"] = "MAYBE"; self.assertIn("CK_KNOWLEDGE_ITEM", check_ck(c))
    def test_fbs_copy_rejected(self):
        f = dict(self.b["examples"][0]["fbs"]); f["behaviour_actual"] = f["behaviour_expected"]; self.assertIn("FBS_ACTUAL_COPIES_EXPECTED", check_fbs(f))
    def test_fbs_unknown_actual_accepted(self):
        self.assertEqual(check_fbs(self.b["examples"][0]["fbs"]), [])

def _dup(pairs):
    o = {}
    for k, v in pairs:
        if k in o:
            raise ValueError("JSON_DUPLICATE_KEY:" + k)
        o[k] = v
    return o

def _const(x):
    raise ValueError("JSON_NONFINITE:" + x)

def main(a):
    if a == ["--self-test"]:
        r = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        return 0 if r.wasSuccessful() else 1
    if len(a) != 1:
        print("Usage: check_a4.py --self-test | payload_a4.json", file=sys.stderr); return 2
    try:
        data = json.loads(Path(a[0]).read_text(encoding="utf-8"), object_pairs_hook=_dup, parse_constant=_const)
        e, w = check(data)
    except (OSError, ValueError, RecursionError) as exc:
        print(json.dumps({"load_error": str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps({"errors": e, "warnings": w, "scope": "STRUCTURAL_A4_ONLY"}, ensure_ascii=False, indent=2))
    return 1 if e else 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
