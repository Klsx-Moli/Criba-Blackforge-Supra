"""No models, SUPRA calls, GUI or remote files. Exercises real pure module."""
import hashlib
import sqlite3
from copy import deepcopy

import pytest

from criba.invention_lineage import bind_entry_to_sheet, verify_archived_invention


ENTRY = {
    "candidate_id": "candidate-a", "estado_interpretacion": "PROPUESTA",
    "hipotesis": "Recover water", "mecanismo": "Route the first flow",
    "interpretacion_error": "", "interprete_result": {"estado": "PROPUESTA", "error": ""},
}


def sheet():
    return {"run_id": "run-12", "query": "Recover initial water", "entries": [deepcopy(ENTRY)]}


def row():
    s = sheet()
    return {"status": "PROPUESTA", "query": s["query"],
            "query_hash": hashlib.sha256(s["query"].encode()).hexdigest(),
            "current_id": "candidate-a",
            "packet": {"kind": "invention_sheet", "sheet": s, "selected_index": 0}}


def test_bind_does_not_mutate_and_preserves_run_identity():
    s = sheet()
    original = deepcopy(s)
    e = bind_entry_to_sheet(s, s["entries"][0])
    assert e["run_id"] == "run-12" and s == original
    e["mecanismo"] = "mutated"
    assert s["entries"][0]["mecanismo"] == "Route the first flow"


@pytest.mark.parametrize("bad", [None, "", " different ", False, 0, [], {}])
def test_reject_invalid_sheet_run_id(bad):
    s = sheet()
    s["run_id"] = bad
    if bad is None:
        assert "run_id" not in bind_entry_to_sheet(s, s["entries"][0])
    else:
        with pytest.raises(ValueError):
            bind_entry_to_sheet(s, s["entries"][0])


def test_mismatch_between_candidate_and_sheet_rejected():
    s = sheet()
    s["entries"][0]["run_id"] = "run-b"
    with pytest.raises(ValueError, match="another run"):
        bind_entry_to_sheet(s, s["entries"][0])


def test_duplicate_candidate_id_rejected_even_if_data_differs():
    s = sheet()
    s["entries"].append({**s["entries"][0], "mecanismo": "completely different"})
    with pytest.raises(ValueError):
        bind_entry_to_sheet(s, s["entries"][0])


def test_foreign_candidate_id_and_contents_rejected():
    s = sheet()
    with pytest.raises(ValueError):
        bind_entry_to_sheet(s, {**s["entries"][0], "mecanismo": "foreign"})
    with pytest.raises(ValueError):
        bind_entry_to_sheet(s, {**s["entries"][0], "candidate_id": "foreign"})


@pytest.mark.parametrize("name", ["query", "problema"])
def test_cross_problem_declared_in_entry_rejected(name):
    s = sheet()
    s["entries"][0][name] = "Other problem"
    with pytest.raises(ValueError):
        bind_entry_to_sheet(s, s["entries"][0])


def test_archival_row_consistency_on_sqlite_restart(tmp_path):
    r = row()
    database = tmp_path / "phase12.sqlite"
    con = sqlite3.connect(database)
    con.execute("CREATE TABLE saved (id TEXT PRIMARY KEY, query TEXT, query_hash TEXT, "
                "current_id TEXT, status TEXT, packet_json TEXT)")
    import json
    con.execute("INSERT INTO saved VALUES (?, ?, ?, ?, ?, ?)",
                ("archive-a", r["query"], r["query_hash"], r["current_id"],
                 r["status"], json.dumps(r["packet"])))
    con.commit()
    con.close()
    con = sqlite3.connect(database)
    data = con.execute("SELECT query,query_hash,current_id,status,packet_json "
                       "FROM saved WHERE id='archive-a'").fetchone()
    recovered = {"query": data[0], "query_hash": data[1], "current_id": data[2],
                 "status": data[3], "packet": json.loads(data[4])}
    verify_archived_invention(recovered)
    con.close()


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(query="other"),
    lambda r: r.update(query_hash="0"*64),
    lambda r: r.update(current_id="other"),
    lambda r: r.update(status="PENDIENTE_INTERPRETACION"),
    lambda r: r["packet"].update(kind="legacy"),
    lambda r: r["packet"].update(selected_index=True),
    lambda r: r["packet"].update(selected_index=5),
    lambda r: r["packet"]["sheet"].update(query="other"),
    lambda r: r["packet"]["sheet"].update(run_id=" run-12 "),
    lambda r: r["packet"]["sheet"]["entries"][0].update(run_id="foreign"),
    lambda r: r["packet"]["sheet"]["entries"][0].update(hipotesis=""),
    lambda r: r["packet"]["sheet"]["entries"][0].update(estado_interpretacion="ERROR"),
    lambda r: r["packet"]["sheet"]["entries"][0].update(interpretacion_error="timeout"),
    lambda r: r["packet"]["sheet"]["entries"][0]["interprete_result"].update(estado="ERROR"),
    lambda r: r["packet"]["sheet"]["entries"][0]["interprete_result"].pop("error"),
])
def test_parseable_corruption_not_promoted(mutate):
    r = row()
    mutate(r)
    with pytest.raises(ValueError):
        verify_archived_invention(r)


def test_legacy_sheet_without_run_id_still_readable():
    r = row()
    r["packet"]["sheet"].pop("run_id")
    verify_archived_invention(r)
