from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

WORKER = r"""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys

def deny_network(*args, **kwargs):
    raise RuntimeError('EF04 storage worker: network is forbidden')
socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network

source = os.environ.get('CBS_EF04_AUDIT_SOURCE')
if source:
    if os.environ.get('CBS_EF04_ALLOW_AUDIT') != 'YES_EXCERPT_ONLY':
        raise RuntimeError('Audit source requires explicit opt-in')
    spec = importlib.util.spec_from_file_location('cbs_audit_module', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mode = 'AUDIT_EXCERPT_NOT_FULL_REPOSITORY'
else:
    module = importlib.import_module('criba.supra_dossier')
    mode = 'REAL_PROJECT_MODULE_DIAGNOSTIC'
expected = os.environ.get('CBS_EF04_EXPECTED_SOURCE')
if expected and Path(module.__file__).resolve() != Path(expected).resolve():
    raise RuntimeError('Wrong imported project module')
request = json.load(sys.stdin)
directory = Path(request['directory']) if request.get('directory') else None
try:
    operation = request['operation']
    if operation == 'save':
        value = str(module.guardar_dossier(request['payload'], directory))
    elif operation == 'load':
        value = module.cargar_dossier(request['identity'], directory)
    elif operation == 'latest':
        value = module.cargar_ultimo_dossier(directory)
    else:
        raise ValueError('Unknown diagnostic operation')
    result = {'ok':True, 'value':value}
    code = 0
except Exception as exc:
    result = {'ok':False,'error_type':type(exc).__name__,'error':str(exc)}
    code = 3
result.update(pid=os.getpid(),module_path=str(Path(module.__file__).resolve()),mode=mode)
print(json.dumps(result,ensure_ascii=False))
sys.exit(code)
"""


def dossier(identity="dossier-ef04-valid"):
    return {
        "dossier_id": identity,
        "candidate_id": "candidate-ef04",
        "claim_id": "claim-ef04",
        "protocol_version": "fixture-v1",
        "mechanism_version": "fixture-mechanism-v1",
        "problema": "SIMULATED: prueba de almacenamiento, no experimento científico",
        "hipotesis": "Texto declarado",
        "mecanismo": "Mecanismo no acreditado",
        "estado": "SUPRA_EJECUCION_PENDIENTE",
        "creado_at": "2026-10-25T00:00:00+00:00",
        "prueba_discriminante": {"observable": "dato declarado", "estado_prueba": "NO_EJECUTADA"},
        "interpretacion": {
            "provenance": {
                "source": "SIMULATED_TEST_FIXTURE",
                "semantic_validation": "NOT_VALIDATED",
            }
        },
        "evidence_delivered": [{"id": "fixture", "text": "áéíóú → recuperación"}],
        "unknown": None,
        "measured_zero": 0.0,
    }


def invoke(home, operation, *, payload=None, identity=None, directory=None):
    env = os.environ.copy()
    env["CRIBASHADOW_HOME"] = str(home)
    env["LOCALAPPDATA"] = str(home / "fallback_localappdata")
    env["SUPRA_USE_MODEL"] = "false"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    source_root = str(Path(__file__).resolve().parents[3] / "src")
    existing_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        source_root + os.pathsep + existing_path if existing_path else source_root
    )
    env.pop("SUPRA_ENDPOINT", None)
    request = {
        "operation": operation,
        "payload": payload,
        "identity": identity,
        "directory": str(directory) if directory else None,
    }
    run = subprocess.run(
        [sys.executable, "-c", WORKER],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=20,
    )
    assert run.returncode in (0, 3), run.stdout + run.stderr
    lines = [line for line in run.stdout.splitlines() if line.strip()]
    assert lines, run.stderr
    result = json.loads(lines[-1])
    assert result["ok"] == (run.returncode == 0), result
    return result
