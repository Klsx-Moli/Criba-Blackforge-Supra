import importlib
import sys
import time

print("exe", sys.executable, flush=True)
for mod in ("httpx", "pytest", "PySide6", "criba", "supra_agentic", "fastapi"):
    t0 = time.time()
    try:
        m = importlib.import_module(mod)
        where = getattr(m, "__file__", "")
        print(f"OK   {mod} {getattr(m, '__version__', '')} {time.time() - t0:.1f}s {where}", flush=True)
    except BaseException as exc:  # noqa: BLE001
        print(f"FAIL {mod} {type(exc).__name__}: {exc} {time.time() - t0:.1f}s", flush=True)