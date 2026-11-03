"""Product presentation; preserves remote channels and adds local state, ES/EN."""
from __future__ import annotations

import copy
import json
import weakref
from typing import Any

from ..dossier_workflow import SCHEMA
from . import i18n


def bind_language(window: Any) -> None:
    if getattr(window, "_dossier_workflow_listener", None) is not None:
        return
    try:
        reference = weakref.ref(window)
    except TypeError:
        return

    def refresh() -> None:
        current = reference()
        if current is not None:
            report = getattr(current, "_dossier_workflow_report", None)
            if isinstance(report, dict):
                try:
                    apply_dossier_report(current, report)
                except RuntimeError:
                    return

    window._dossier_workflow_listener = refresh
    i18n.on_change(refresh)
    weakref.finalize(window, i18n.off_change, refresh)
    destroyed = getattr(window, "destroyed", None)
    if destroyed is not None and hasattr(destroyed, "connect"):
        destroyed.connect(lambda *_args: i18n.off_change(refresh))


def apply_dossier_report(window: Any, report: dict[str, Any]) -> None:
    if report.get("workflow_schema") != SCHEMA:
        return
    window._dossier_workflow_report = copy.deepcopy(report)
    bind_language(window)
    candidates = getattr(window, "candidates", None)
    if candidates is None:
        return
    dossier = report.get("dossier")
    widget = getattr(candidates, "dossier_output", None)
    if widget is not None:
        if isinstance(dossier, dict):
            widget.setPlainText(json.dumps(dossier, ensure_ascii=False, indent=2))
        else:
            widget.clear()
    output = getattr(candidates, "supra_output", None)
    if output is not None:
        output.setPlainText(json.dumps(report, ensure_ascii=False, indent=2))
    refs = getattr(window, "refs", {})
    summary = refs.get("ideaSummary") if isinstance(refs, dict) else None
    if summary is not None:
        base = summary.text()
        old = getattr(window, "_dossier_workflow_suffix", "")
        if old and base.endswith(old):
            base = base[:-len(old)]
        key = "dossier.local." + str(report.get("local_dossier_status") or "UNKNOWN")
        reason = i18n.t(key)
        if reason == key:
            reason = i18n.t("dossier.local.UNKNOWN")
        suffix = " · " + i18n.t("dossier.local.label") + ": " + reason
        window._dossier_workflow_suffix = suffix
        summary.setText(base + suffix)
