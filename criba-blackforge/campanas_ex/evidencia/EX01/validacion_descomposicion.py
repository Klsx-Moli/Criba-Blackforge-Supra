"""Validacion reproducible de la descomposicion EX01.

Ejecutar:
  .venv/Scripts/python.exe campanas_ex/evidencia/EX01/validacion_descomposicion.py
"""
from __future__ import annotations
import json, os, sys, yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# ROOT -> criba-blackforge
CANON = os.path.join(ROOT, "data", "intelligence", "technique_registry.yaml")
BACKLOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backlog_lotes.json")

d = yaml.safe_load(open(CANON, encoding="utf-8"))
tech = {t["id"]: t for t in d["techniques"]}
planned = {t["id"] for t in d["techniques"] if t["status"] == "PLANNED"}
implemented = {t["id"] for t in d["techniques"] if t["status"].startswith("IMPLEMENTED")}
b = json.load(open(BACKLOG, encoding="utf-8"))

errors = []
# 1. count
if b["total_planned"] != len(planned):
    errors.append(f"total_planned {b['total_planned']} != canon planned {len(planned)}")
# 2. sum counts
if sum(l["count"] for l in b["lots"]) != len(planned):
    errors.append(f"sum counts {sum(l['count'] for l in b['lots'])} != {len(planned)}")
# 3. unique ids, no dup
ids = [i for l in b["lots"] for i in l["ids"]]
if len(ids) != len(set(ids)):
    from collections import Counter
    dup = [k for k,v in Counter(ids).items() if v>1]
    errors.append(f"duplicate ids in lots: {dup}")
# 4. no overlap with implemented
if set(ids) & implemented:
    errors.append(f"overlap with IMPLEMENTED: {set(ids)&implemented}")
# 5. all planned covered, no extras
if set(ids) != planned:
    errors.append(f"missing planned: {planned-set(ids)}")
    errors.append(f"extra ids: {set(ids)-planned}")
# 6. family coherence per lot
for lot in b["lots"]:
    fams = {tech[i]["family"] for i in lot["ids"]}
    if len(fams) > 1:
        errors.append(f"{lot['lot_id']}: mixed families {fams}")
    if lot["count"] != len(lot["ids"]):
        errors.append(f"{lot['lot_id']}: count mismatch")
    if lot["est_hours"] <= 0:
        errors.append(f"{lot['lot_id']}: non-positive hours")
# 7. special lots contain expected ids
special_ids = {i for l in b["lots"] if l["lot_id"].startswith("L0_SPECIAL") for i in l["ids"]}
if special_ids != {"T054", "T061", "T104", "T111"}:
    errors.append(f"special lots ids {special_ids} != expected")
# 8. lot count
print("lots:", len(b["lots"]))
print("total planned:", b["total_planned"])
print("sum counts:", sum(l["count"] for l in b["lots"]))
print("unique ids:", len(set(ids)))
print("errors:", len(errors))
for e in errors:
    print("  ERROR:", e)
if errors:
    sys.exit(1)
print("VALIDATION OK")
