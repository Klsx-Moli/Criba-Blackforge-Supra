"""Fail CI only when mypy introduces type debt beyond the explicit baseline."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "ci" / "mypy_baseline.json"
ERROR_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+): error: (?P<message>.+?)  \[(?P<code>[^\]]+)\]$"
)


def _fingerprints(output: str) -> Counter[tuple[str, str, str]]:
    result: Counter[tuple[str, str, str]] = Counter()
    for raw in output.splitlines():
        match = ERROR_RE.match(raw.strip())
        if not match:
            continue
        path = match.group("path").replace("\\\\", "/").replace("\\", "/")
        result[(path, match.group("code"), match.group("message"))] += 1
    return result


def main() -> int:
    baseline_data = json.loads(BASELINE.read_text(encoding="utf-8"))
    allowed: Counter[tuple[str, str, str]] = Counter()
    for item in baseline_data["fingerprints"]:
        allowed[(item["path"], item["code"], item["message"])] = int(item["count"])

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "src/criba",
            "--show-error-codes",
            "--no-pretty",
            "--no-color-output",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(proc.stdout, end="")

    if proc.returncode not in (0, 1):
        print(f"mypy execution failed with exit code {proc.returncode}", file=sys.stderr)
        return proc.returncode or 2

    current = _fingerprints(proc.stdout)
    regressions = current - allowed
    removed = allowed - current

    print(
        f"mypy debt gate: current={sum(current.values())}, "
        f"baseline={sum(allowed.values())}, new={sum(regressions.values())}, "
        f"removed={sum(removed.values())}"
    )

    if regressions:
        print("New mypy debt detected:", file=sys.stderr)
        for (path, code, message), count in sorted(regressions.items()):
            print(f"  {count}x {path} [{code}] {message}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
