"""Observational-only Anti-Goodhart support.

This package is intentionally not imported by CRIBA's decisional runtime.
STANDARD consumes sealed post-run traces out of band and never writes back
into selection, prompts, memory, priors, scoring, or learning.
"""

from .gate import GateEvidence, ObserverMode, StandardDisabledError, standard_allowed
from .trace import (
    SealedTrace,
    load_sealed_trace,
    project_public_packet,
    seal_public_packet,
    sealed_trace_record,
)

__all__ = [
    "GateEvidence",
    "ObserverMode",
    "SealedTrace",
    "StandardDisabledError",
    "load_sealed_trace",
    "project_public_packet",
    "seal_public_packet",
    "sealed_trace_record",
    "standard_allowed",
]
