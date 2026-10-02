"""Canonical serialization for evidence hashes.

These two helpers hash the content of an evidence record, so their exact byte
output is load-bearing: every hash already written into the invention ledger
was produced by this code. They therefore live here, in a module with no
BLACKFORGE meaning, rather than inside a BLACKFORGE-named module that CRIBA
Core had to import just to hash something.

``criba.blackforge_causal`` re-exports these exact objects. There is one
implementation and one set of golden vectors; the identity is pinned by
``tests/unit/test_blackforge_isolation_gate.py`` so the two import paths can
never drift apart and silently split the ledger in two.

``allow_nan=False`` is deliberate. A NaN or +/-Infinity is a value this system
cannot represent, and letting it serialize would give "not representable" and
"absent" the same hash. UNKNOWN must never be able to pose as a value.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

__all__ = ["canonical_json", "canonical_hash"]


def canonical_json(value: Any) -> str:
    """Serialize deterministically: sorted keys, compact, UTF-8, no NaN."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_hash(value: Any) -> str:
    """Hash the canonical serialization of ``value``."""
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()
