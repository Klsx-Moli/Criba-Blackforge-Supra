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
    start = source.index("function setUIState")
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
