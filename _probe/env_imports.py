import importlib
import sys
import time

for mod in ("httpx", "pytest", "fastapi", "criba", "PySide6"):
    t0 = time.time()
    try:
        m = importlib.import_module(mod)
        print(f"OK   {mod} {getattr(m, '__version__', '')} {time.time() - t0:.1f}s", flush=True)
    except BaseException as exc:  # noqa: BLE001
        print(f"FAIL {mod} {type(exc).__name__}: {exc} {time.time() - t0:.1f}s", flush=True)