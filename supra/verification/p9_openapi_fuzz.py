"""P9 · Fuzzing de la API SUPRA: genera casos con schemathesis, ejecuta con TestClient.

Storage de TEST aislado (SUPRA_STORAGE_DIR temporal, fijado ANTES del import porque
state_manager es singleton a nivel de módulo). Nunca datos productivos.

Genera 1 caso schema-compliant por endpoint con schemathesis y lo ejecuta contra la app
ASGI vía FastAPI TestClient, capturando el status. Reporta:
  - inventario de endpoints OpenAPI,
  - cualquier 5xx (inesperado),
  - rechazos de dato schema-compliant (brecha schema<->código).
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("SUPRA_USE_MODEL", "false")
os.environ.setdefault("SUPRA_STORAGE_DIR", tempfile.mkdtemp(prefix="p9-fuzz-"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import schemathesis  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from supra_agentic.service import app  # noqa: E402


def main() -> int:
    schema = schemathesis.openapi.from_asgi("/openapi.json", app)
    operations = list(schema.get_all_operations())
    print(f"Operaciones descubiertas en OpenAPI de SUPRA: {len(operations)}")
    for op in operations:
        ok_op = op.ok()
        print(f"  {ok_op.method.upper()} {ok_op.full_path}")

    client = TestClient(app)
    five_xx: list[str] = []
    rejected_positive: list[str] = []
    tested = 0
    for op in operations:
        ok_op = op.ok()
        method = ok_op.method.upper()
        path = ok_op.full_path
        try:
            case = ok_op.as_strategy().example()
        except Exception as exc:  # noqa: BLE001
            rejected_positive.append(f"{method} {path} no-strategy {type(exc).__name__}")
            continue
        tested += 1
        try:
            concrete = path
            params = getattr(case, "path_parameters", {}) or {}
            for name in params:
                concrete = concrete.replace("{" + name + "}", str(params[name]))
            kwargs = {}
            body = getattr(case, "body", None)
            # schemathesis usa NotSet como centinela; no es JSON serializable.
            if body is not None and type(body).__name__ != "NotSet":
                kwargs["json"] = body
            resp = client.request(method, concrete, **kwargs)
            status = resp.status_code
            if status >= 500:
                five_xx.append(f"{method} {concrete} -> {status}")
            elif status in (400, 422):
                rejected_positive.append(f"{method} {concrete} -> {status}")
        except Exception as exc:  # noqa: BLE001
            five_xx.append(f"{method} {path} EXC {type(exc).__name__}: {str(exc)[:80]}")

    print(f"\nEjemplos ejecutados: {tested}")
    if five_xx:
        print(f"\n5xx INESPERADOS (acceptance fallido): {len(five_xx)}")
        for h in five_xx:
            print(f"  {h}")
    if rejected_positive:
        print(f"\nBrechas schema<->código (dato schema-compliant rechazado 4xx): {len(rejected_positive)}")
        for h in rejected_positive:
            print(f"  {h}")
    if not five_xx:
        print("\nVEREDICTO: 0 5xx inesperados. " +
              ("Hallazgos de brecha schema documentados arriba." if rejected_positive
               else "Sin hallazgos."))
        return 0 if not rejected_positive else 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
