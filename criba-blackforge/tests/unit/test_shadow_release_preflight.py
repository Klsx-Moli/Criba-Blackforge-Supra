"""No release can be marked visually accepted by an offscreen/startup flag."""
from scripts.verify_shadow_windows import assess_startup_trace

SUCCESSFUL_TRACE = [
    "main:entered",
    "lock:True",
    "paths:wired",
    "supra:ready",
    "qt:application",
    "qt:window-created",
    "qt:window-shown visible=True minimized=False winid=42",
    "qt:restore-started",
]


def test_complete_trace_is_only_a_startup_smoke():
    result = assess_startup_trace(SUCCESSFUL_TRACE, process_alive=True)
    assert result["status"] == "STARTUP_SMOKE_PASS"
    assert result["desktop_visual_acceptance"] == "NOT_VERIFIED"
    assert result["exe_functional_end_to_end_acceptance"] == "NOT_VERIFIED"


def test_missing_supra_backend_is_not_pass():
    result = assess_startup_trace(
        [x for x in SUCCESSFUL_TRACE if x != "supra:ready"], process_alive=True
    )
    assert result["status"] == "STARTUP_SMOKE_FAIL"


def test_hidden_or_minimized_window_is_not_pass():
    for bad in ("qt:window-shown visible=False minimized=False winid=42",
                "qt:window-shown visible=True minimized=True winid=42"):
        trace = [bad if x.startswith("qt:window-shown ") else x for x in SUCCESSFUL_TRACE]
        assert assess_startup_trace(trace, process_alive=True)["status"] == "STARTUP_SMOKE_FAIL"


def test_crashed_process_and_missing_restore_are_not_pass():
    assert assess_startup_trace(SUCCESSFUL_TRACE, False)["status"] == "STARTUP_SMOKE_FAIL"
    trace = [x for x in SUCCESSFUL_TRACE if x != "qt:restore-started"]
    assert assess_startup_trace(trace, True)["status"] == "STARTUP_SMOKE_FAIL"
