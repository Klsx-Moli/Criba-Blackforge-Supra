from pathlib import Path
import subprocess

APP_JS = Path(__file__).parents[2] / "src" / "supra_agentic" / "web" / "app.js"


def test_ui_dynamic_model_strings_are_html_escaped():
    source = APP_JS.read_text(encoding="utf-8")
    required = [
        "escapeHtml(posture.objective)",
        "escapeHtml(inv)",
        "escapeHtml(mut)",
        "escapeHtml(c.pathway_name)",
        "escapeHtml(c.paradigm_type)",
        "escapeHtml(c.hypothesis)",
        "escapeHtml(ver ? ver.rationale",
        "escapeHtml(rex.output_log)",
        "escapeHtml(chk.evidence_summary)",
        "escapeHtml(p.objective.substring(0, 35))",
    ]
    for sentinel in required:
        assert sentinel in source


def test_escape_html_blocks_markup_payload_in_actual_js_helper():
    source = APP_JS.read_text(encoding="utf-8")
    start = source.index("function escapeHtml")
    end = source.index("\n}\n", start) + 3
    helper = source[start:end]
    script = helper + "\nconsole.log(escapeHtml(`<img src=x onerror=alert('x')>&\\\"`));"
    result = subprocess.run(
        ["node", "-e", script], check=True, capture_output=True, text=True
    )
    escaped = result.stdout.strip()
    assert "<img" not in escaped
    assert "onerror=alert" in escaped
    assert "&lt;img" in escaped
    assert "&amp;" in escaped
    assert "&quot;" in escaped


def test_blocked_ui_never_marks_stepper_completion_in_actual_js():
    source = APP_JS.read_text(encoding="utf-8")
    start = source.index("function currentAuthoritativeExecution")
    end = source.index("\nfunction renderProjectPosture", start)
    helper = source[start:end]
    script = r'''
const states = {};
function element(id) {
  if (!states[id]) states[id] = {
    innerText: '',
    classList: {
      values: new Set(),
      remove(...xs) { xs.forEach(x => this.values.delete(x)); },
      add(x) { this.values.add(x); },
      contains(x) { return this.values.has(x); }
    }
  };
  return states[id];
}
const document = { getElementById: element };
const window = {};
''' + helper + r'''
setUIState('BLOCKED', 'BLOCKED', {restricted_execution_results: []});
const stepIds = ['received','structured','stratified','restricted','completed'];
const completed = stepIds.filter(s => element(`step-${s}`).classList.contains('completed'));
console.log(JSON.stringify({tag: element('current-stage-tag').innerText, completed}));
'''
    result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
    import json
    observed = json.loads(result.stdout)
    assert observed == {"tag": "BLOCKED", "completed": []}


def test_ui_restricted_step_uses_current_attempt_not_last_historical_result():
    source = APP_JS.read_text(encoding="utf-8")
    start = source.index("function currentAuthoritativeExecution")
    end = source.index("\nfunction renderProjectPosture", start)
    helper = source[start:end]
    prefix = r"""
const states = {};
function element(id) {
  if (!states[id]) states[id] = {
    innerText: '',
    classList: {
      values: new Set(),
      remove(...xs) { xs.forEach(x => this.values.delete(x)); },
      add(x) { this.values.add(x); },
      contains(x) { return this.values.has(x); }
    }
  };
  return states[id];
}
const document = { getElementById: element };
const window = {};
"""
    suffix = r"""
const currentAttempt = 'attempt-' + 'a'.repeat(32);
const staleAttempt = 'attempt-' + 'b'.repeat(32);
const posture = {
  restricted_execution_attempt_id: currentAttempt,
  restricted_execution_generation: 2,
  restricted_execution_results: [
    {attempt_id: currentAttempt, attempt_generation: 2, passed: true, identity_bound: true},
    {attempt_id: staleAttempt, attempt_generation: 1, passed: false, identity_bound: false}
  ]
};
setUIState('COMPLETED', 'COMPLETED', posture);
console.log(JSON.stringify({
  restrictedCompleted: element('step-restricted').classList.contains('completed'),
  completedActive: element('step-completed').classList.contains('active')
}));
"""
    result = subprocess.run(["node", "-e", prefix + helper + suffix], check=True, capture_output=True, text=True)
    import json
    observed = json.loads(result.stdout)
    assert observed == {"restrictedCompleted": True, "completedActive": True}



def test_ui_rejects_generation_outside_javascript_safe_integer_range():
    source = APP_JS.read_text(encoding="utf-8")
    start = source.index("function currentAuthoritativeExecution")
    end = source.index("\nfunction setUIState", start)
    helper = source[start:end]
    script = helper + r"""
const id = 'attempt-' + 'a'.repeat(32);
const unsafeA = JSON.parse('{\"g\":9007199254740992}').g;
const unsafeB = JSON.parse('{\"g\":9007199254740993}').g;
const posture = {
  restricted_execution_attempt_id: id,
  restricted_execution_generation: unsafeA,
  restricted_execution_results: [
    {attempt_id: id, attempt_generation: unsafeB, passed: true, identity_bound: true}
  ]
};
console.log(JSON.stringify({
  jsonCollision: unsafeA === unsafeB,
  authority: currentAuthoritativeExecution(posture)
}));
"""
    result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
    import json
    observed = json.loads(result.stdout)
    assert observed["jsonCollision"] is True
    assert observed["authority"] is None
