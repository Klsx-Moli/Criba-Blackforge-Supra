"""Acceptance-only native Nous proxy with a durable physical upstream budget.

Run using Hermes's Python environment. No installed Hermes source/config is edited.
All native OAuth retry attempts pass through the same durable reservation.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.acceptance_http_budget import BudgetLedger, install_native_budget  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--model", default="poolside/laguna-s-2.1:free")
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()
    from hermes_cli.proxy import server
    from hermes_cli.proxy.adapters import get_adapter

    adapter = get_adapter("nous")
    if not adapter.is_authenticated():
        raise RuntimeError("Existing Nous authentication is not available")
    ledger = BudgetLedger(
        args.ledger,
        args.model,
        "http://127.0.0.1:8645/v1",
        initialize=args.initialize,
    )
    install_native_budget(server, ledger)
    print(
        f"PHYSICAL_UPSTREAM_GUARD_READY model={args.model} "
        f"used={ledger.used} max=12",
        flush=True,
    )
    asyncio.run(server.run_server(adapter, host="127.0.0.1", port=8645))


if __name__ == "__main__":
    main()
