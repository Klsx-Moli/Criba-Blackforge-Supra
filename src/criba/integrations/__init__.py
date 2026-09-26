"""Typed external integration clients for CRIBA."""

from .supra_client import (
    SupraClient,
    SupraClientConfig,
    SupraClientError,
    SupraProjectResult,
    objective_from_dossier,
)

__all__ = [
    "SupraClient",
    "SupraClientConfig",
    "SupraClientError",
    "SupraProjectResult",
    "objective_from_dossier",
]
