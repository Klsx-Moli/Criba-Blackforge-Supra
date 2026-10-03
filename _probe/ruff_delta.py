"""Compare ruff findings on the M3-touched files against the committed baseline.

The CRIBA repo carries a large amount of pre-existing ruff noise, so a raw
"ruff check src tests" count says nothing about this change. What matters is
whether M3 ADDED findings. This stashes nothing and writes nothing: it ruff-checks
the working tree, then ruff-checks the same paths as they exist in HEAD (via
`git show` into a temp copy), and prints the delta.

Usage: python _probe/ruff_delta.py <repo_root>
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(sys.argv[1])
RUFF = REPO_ROOT / ".venv" / "Scripts" / "ruff.exe"

PATHS = [
    "src/criba/ui/actions.py",
    "src/criba/integrations/supra_client.py",
    "tests/integration/test_m2_read_path_channels.py",
    "tests/integration/test_m2_vertical_slice_e2e.py",
    "tests/integration/test_supra_client_contract.py",
]

RULE = re.compile(r"^([A-Z]+[0-9]+)\s", re.MULTILINE)


def findings(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for code in RULE.findall(text):
        counts[code] = counts.get(code, 0) + 1
    return counts


def ruff(paths: list[str], cwd: Path) -> str:
    proc = subprocess.run(
        [str(RUFF), "check", *paths, "--output-format", "concise"],
        cwd=str(cwd), capture_output=True, text=True, timeout=600,
    )
    return proc.stdout + proc.stderr


def main() -> int:
    current = ruff(PATHS, REPO_ROOT)
    print("=== working tree ===")
    print(current.strip()[-400:] or "(sin hallazgos)")

    baseline_dir = Path(tempfile.mkdtemp(prefix="astra-ruff-base-"))
    # The monorepo root is the parent of the component root: `git show` needs
    # the repo-relative path, otherwise every lookup fails and the baseline
    # comes out empty, which would silently report "0 new findings".
    git_root = REPO_ROOT.parent
    prefix = REPO_ROOT.name
    for rel in PATHS:
        repo_rel = f"{prefix}/{rel}".replace("\\", "/")
        proc = subprocess.run(
            ["git", "-C", str(git_root), "show", f"HEAD:{repo_rel}"],
            capture_output=True, text=True, encoding="utf-8",
        )
        if proc.returncode != 0:
            print(f"  (HEAD no tiene {repo_rel}; se omite del baseline)")
            continue
        out = baseline_dir / Path(rel).name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(proc.stdout, encoding="utf-8")

    baseline_names = [p.name for p in sorted(baseline_dir.glob("*.py"))]
    if not baseline_names:
        print("BASELINE VACIO: no se puede afirmar nada sobre el delta.")
        return 2
    base_out = subprocess.run(
        [str(RUFF), "check", *baseline_names, "--output-format", "concise"],
        cwd=str(baseline_dir), capture_output=True, text=True, timeout=600,
    ).stdout

    now_counts = findings(current)
    base_counts = findings(base_out)
    print("\n=== delta M3 (working tree - HEAD) ===")
    added = {k: v - base_counts.get(k, 0) for k, v in now_counts.items()}
    added = {k: v for k, v in added.items() if v > 0}
    if not added:
        print("0 hallazgos nuevos atribuibles a M3")
        return 0
    for code, count in sorted(added.items()):
        print(f"  +{count} {code}")
    return 1


if __name__ == "__main__":
    sys.exit(main())