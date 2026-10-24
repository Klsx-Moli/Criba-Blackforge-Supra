"""Corpus-local attribute-substitution hypotheses (P09-T04 / T061).

T061 is declared in the invention taxonomy (``attribute_substitution``) and in
the technique registry (``criba.intelligence.invention.recombination``) but had
no module. This implementation follows the same evidence-bounded contract as
T053: a document contributes only when its metadata declares an explicit
``attributes`` mapping (name -> value). Prose and unrelated metadata are not
inferred, so the operator never manufactures an attribute from text, length or
format.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import permutations

from ..contracts import EvidenceDocument, InventionCandidate


def _attributes(document: EvidenceDocument) -> tuple[tuple[str, str], ...]:
    """Read explicit textual attributes; missing values never become evidence.

    A value must be an explicit string. ``None`` is absence and is skipped;
    other non-string types (booleans, numbers, containers) are an undeclared
    shape and raise ``TypeError`` rather than being coerced with ``str()`` —
    coercing would turn an absent value into the literal text ``"None"`` and a
    list into its ``repr``, converting absence/structure into a declared
    attribute.
    """

    metadata = document.metadata
    if metadata is None:
        return ()
    if not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping or None")
    raw = metadata.get("attributes")
    if raw is None:
        return ()
    if not isinstance(raw, Mapping):
        raise TypeError("metadata.attributes must be a mapping or None")
    out: set[tuple[str, str]] = set()
    for name, value in raw.items():
        if name is None or value is None:
            continue
        if not isinstance(name, str) or not isinstance(value, str):
            raise TypeError("attribute names and values must be explicit strings")
        name_s, value_s = name.strip(), value.strip()
        if name_s and value_s:
            out.add((name_s, value_s))
    return tuple(sorted(out))


def substitute_attributes(
    documents: Sequence[EvidenceDocument], *, limit: int = 20
) -> list[InventionCandidate]:
    """Return deterministic, corpus-local T061 hypotheses.

    A hypothesis proposes substituting the value of one attribute for the value
    of another attribute observed in the same corpus, preserving the attribute
    name. It remains a hypothesis: the corpus can be incomplete, and the
    substitution is not evidence that the new value solves the problem.
    """

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be a non-negative integer")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if isinstance(documents, str) or not isinstance(documents, (list, tuple, set)):
        raise TypeError("documents must be a sequence of EvidenceDocument values")

    # attribute name -> set of observed values (across the supplied corpus)
    values_by_attribute: dict[str, set[str]] = {}
    for document in documents:
        if not isinstance(document, EvidenceDocument):
            raise TypeError("documents must contain EvidenceDocument values")
        for name, value in _attributes(document):
            values_by_attribute.setdefault(name, set()).add(value)

    candidates: list[InventionCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    for name, values in sorted(values_by_attribute.items()):
        if len(values) < 2:
            # A single observed value has nothing to substitute against.
            continue
        ordered = sorted(values)
        for current, proposed in permutations(ordered, 2):
            key = (name, current, proposed)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                InventionCandidate(
                    title=f"Substitute {name}={current} with {proposed}",
                    description=(
                        f"Corpus-local T061 hypothesis: the attribute '{name}' takes "
                        f"the observed values {', '.join(ordered)} in the supplied "
                        f"documents; substituting '{current}' for '{proposed}' is a "
                        f"candidate change. This is not evidence that the new value "
                        f"solves the problem."
                    ),
                    operators=("T061",),
                )
            )
    return candidates[:limit]


def _technologies(document: EvidenceDocument) -> tuple[str, ...]:
    """Read explicit source technologies only; no technology is inferred from prose."""

    raw = document.metadata.get("technologies")
    if not isinstance(raw, Mapping):
        return ()
    out: list[str] = []
    for name in raw.keys():
        if not isinstance(name, str):
            continue
        name_s = name.strip()
        if name_s:
            out.append(name_s)
    return tuple(sorted(set(out)))


def recombine_technologies(
    documents: Sequence[EvidenceDocument], *, limit: int = 20
) -> list[InventionCandidate]:
    """Return deterministic, corpus-local T054 hypotheses.

    A hypothesis proposes combining two technologies explicitly declared in the
    supplied corpus. It remains a hypothesis: the corpus can be incomplete, and
    the combination is not evidence of feasibility, novelty or usefulness.
    """

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be a non-negative integer")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if isinstance(documents, str) or not isinstance(documents, (list, tuple, set)):
        raise TypeError("documents must be a sequence of EvidenceDocument values")

    technologies: set[str] = set()
    for document in documents:
        if not isinstance(document, EvidenceDocument):
            raise TypeError("documents must contain EvidenceDocument values")
        technologies.update(_technologies(document))

    ordered = sorted(technologies)
    candidates: list[InventionCandidate] = []
    seen: set[tuple[str, str]] = set()
    for i, left in enumerate(ordered):
        for right in ordered[i + 1:]:
            key = (left, right)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                InventionCandidate(
                    title=f"Combine {left} + {right}",
                    description=(
                        f"Corpus-local T054 hypothesis: the technologies '{left}' and "
                        f"'{right}' are explicitly declared in the supplied documents; "
                        f"combining them is a candidate. This is not evidence of "
                        f"feasibility, novelty or usefulness."
                    ),
                    operators=("T054",),
                )
            )
    return candidates[:limit]
