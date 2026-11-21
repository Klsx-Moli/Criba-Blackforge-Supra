"""Opt-in acceptance of real proposals in both packaged interfaces, then restart.

Started only after start_bundle_probe verifies an isolated test profile. No model,
engine, storage, worker or HTTP response is replaced. Generation requires the
external physical-request budget guard; restoration performs no generation.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import traceback

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QPushButton
from shadow_bundle_probe import verify_rendered_image

PROBLEM = (
    "Reducir el agua desaprovechada al iniciar una ducha doméstica sin contaminar la red potable."
)
BLACKFORGE_PROBLEM = os.environ.get(
    "CRIBA_ACCEPTANCE_BLACKFORGE_PROBLEM",
    (
        "Detectar dependencias npm comprometidas o typosquatting en un monorepo "
        "antes de instalarlas en CI, sin servicios de pago y sin bloquear builds legítimos."
    ),
)
MAX_RUNTIME_S = float(os.environ.get("CRIBA_ACCEPTANCE_MAX_RUNTIME_S", "650"))


def chosen_entry(sheet):
    for index, entry in enumerate(sheet.get("entries", [])):
        if (
            isinstance(entry, dict)
            and entry.get("estado_interpretacion") == "PROPUESTA"
            and str(entry.get("hipotesis") or "").strip()
            and str(entry.get("mecanismo") or "").strip()
        ):
            return index
    raise ValueError("No actual interpreted proposal with a hypothesis and mechanism")


def fingerprint(value):
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


class InventionProbe(QObject):
    def __init__(self, app, window, home, mode):
        super().__init__(window)
        self.app, self.window, self.home, self.mode = app, window, home, mode
        self.directory = home / "bundle-verification"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.started = time.monotonic()
        self.stage = "START"
        self.blackforge = None
        self.expected = {}
        self.report = {
            "status": "IN_PROGRESS",
            "mode": mode,
            "model_output": "REAL_PROVIDER_REQUIRED",
            "response_doubles": False,
            "scientific_benefit": "NOT_ESTABLISHED",
            "desktop_human_visual_review": "NOT_VERIFIED",
            "problems": {"shadow": PROBLEM, "blackforge": BLACKFORGE_PROBLEM},
        }
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(100)
        QTimer.singleShot(700, self.begin)

    def snapshot(self, name, window, min_colors=14):
        self.report["image_" + name] = verify_rendered_image(
            window, self.directory / (name + ".png"), min_colors=min_colors
        )

    def preserve_sheet(self, kind, sheet):
        # Capture failure diagnostics BEFORE validation can close the process.
        # No raw response, prompt, cross records, headers or retrieved corpus.
        fields = (
            "candidate_id",
            "estado_interpretacion",
            "interpretacion_error",
            "interpretacion_error_kind",
            "interpretacion_diagnostico",
            "interpretacion_finish_reason",
            "interpretacion_usage",
            "interpretacion_provenance",
            "interpretacion_model_requests",
        )
        diagnostics = {
            "run_id": sheet.get("run_id"),
            "generated_at": sheet.get("generated_at"),
            "entries": [
                {key: entry.get(key) for key in fields} for entry in sheet.get("entries", [])
            ],
        }
        (self.directory / (kind + "-observed-diagnostics.json")).write_text(
            json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def begin(self):
        try:
            if self.mode == "invention-restore":
                self.restore()
                return
            if (
                self.mode != "invention"
                or os.environ.get("CRIBA_ACCEPTANCE_PHYSICAL_BUDGET") != "12"
            ):
                raise ValueError("Live acceptance requires an explicit external 12-attempt guard")
            os.environ["CRIBA_ACCEPTANCE_NO_RETRIES"] = "1"
            self.window.header.problem_input.setText(PROBLEM)
            self.window.header.problem_input.returnPressed.emit()
            if self.window.problem != PROBLEM:
                raise ValueError("Header did not submit the problem")
            self.window.topcards.btn_gen.click()
            self.stage = "SHADOW_GENERATE"
        except Exception as exc:
            self.fail(exc)

    def poll(self):
        try:
            if time.monotonic() - self.started > MAX_RUNTIME_S:
                raise TimeoutError("Real proposal journey exceeded acceptance deadline")
            if self.stage in {"SHADOW_GENERATE", "BLACKFORGE_GENERATE"}:
                modal = QApplication.activeModalWidget()
                if modal is not None:
                    text = getattr(modal, "text", lambda: "")()
                    raise RuntimeError(
                        f"Modal dialog blocked {self.stage}: "
                        f"{modal.windowTitle()}: {str(text)[:300]}"
                    )
            if self.stage == "SHADOW_GENERATE":
                sheet = self.window.invent_sheet
                if sheet is None or self.window._live_workers:
                    return
                self.preserve_sheet("shadow", sheet)
                index = chosen_entry(sheet)
                self.window.candidates.show_interpreter_entry(index)
                mechanism = sheet["entries"][index]["mecanismo"]
                if mechanism not in self.window.candidates.interpretation_output.toPlainText():
                    raise ValueError("Shadow did not render the provider's mechanism")
                self.window.candidates.save_idea.click()
                ident = self.window.store.list_sessions()[0]["id"]
                self.remember("shadow", ident, sheet)
                self.snapshot("shadow-proposal", self.window)
                if os.environ.get("CRIBA_ACCEPTANCE_SHADOW_ONLY") == "1":
                    (self.directory / "expected-sheets.json").write_text(
                        json.dumps(self.expected, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    self.report["status"] = "REAL_SHADOW_JOURNEY_PASS"
                    self.finish(0)
                    return
                from criba.ui.blackforge_window import BlackforgeWindow

                self.blackforge = BlackforgeWindow(
                    database=str(self.home / "criba.sqlite3"), query=BLACKFORGE_PROBLEM
                )
                self.blackforge.show()
                self.blackforge.execute_button.click()
                self.stage = "BLACKFORGE_GENERATE"
            elif self.stage == "BLACKFORGE_GENERATE":
                if self.blackforge.invent_sheet is None or self.blackforge._busy:
                    return
                sheet = self.blackforge.invent_sheet
                self.preserve_sheet("blackforge", sheet)
                index = chosen_entry(sheet)
                dialog = self.blackforge._proposal_dialog
                dialog.show_entry(index)
                if sheet["entries"][index]["mecanismo"] not in dialog.output.toPlainText():
                    raise ValueError("BLACKFORGE did not render the provider's mechanism")
                dialog.save_button.click()
                self.remember("blackforge", dialog.saved_id, sheet)
                self.snapshot("blackforge-proposal", self.blackforge)
                dialog.resize(1040, 700)
                dialog.show()
                dialog.raise_()
                dialog.activateWindow()
                self.reader_dialog = dialog
                self.reader_ready_at = time.monotonic() + 0.6
                self.stage = "BLACKFORGE_READER"
            elif self.stage == "BLACKFORGE_READER":
                if time.monotonic() < self.reader_ready_at:
                    return
                self.app.processEvents()
                self.snapshot("blackforge-reader", self.reader_dialog, min_colors=4)
                (self.directory / "expected-sheets.json").write_text(
                    json.dumps(self.expected, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                self.report["status"] = "REAL_INVENTION_JOURNEY_PASS"
                self.finish(0)
        except Exception as exc:
            self.fail(exc)

    def remember(self, kind, ident, sheet):
        record = self.window.store.get(ident)
        if record["packet"]["sheet"] != sheet:
            raise ValueError("GUI save differs from actual provider output")
        self.expected[kind] = {"id": ident, "sheet": sheet}
        self.report[kind] = {
            "id": ident,
            "sheet_sha256": fingerprint(sheet),
            "valid_proposals": sum(
                e.get("estado_interpretacion") == "PROPUESTA" for e in sheet["entries"]
            ),
            "entries": len(sheet["entries"]),
            "model_requested": sheet.get("interpreter", {}).get("model_requested"),
        }

    def load_history(self, owner, callback, ident):
        errors = []

        def choose():
            dialog = QApplication.activeModalWidget()
            try:
                if not isinstance(dialog, QDialog):
                    raise ValueError("History dialog is not open")
                listing = dialog.findChild(QListWidget)
                row = next(
                    i
                    for i in range(listing.count())
                    if listing.item(i).data(Qt.ItemDataRole.UserRole) == ident
                )
                listing.setCurrentRow(row)
                button = next(
                    b
                    for b in dialog.findChildren(QPushButton)
                    if b.text() == "Cargar como idea activa"
                )
                button.click()
            except Exception as exc:
                errors.append(type(exc).__name__)
                if isinstance(dialog, QDialog):
                    dialog.reject()

        QTimer.singleShot(150, choose)
        callback()
        if errors:
            raise ValueError("History could not load the exact saved identity")
        if owner.invent_sheet is None:
            raise ValueError("History returned no proposal")

    def restore(self):
        from criba.ui import actions
        from criba.ui.blackforge_window import BlackforgeWindow

        self.expected = json.loads(
            (self.directory / "expected-sheets.json").read_text(encoding="utf-8")
        )
        for item in self.expected.values():
            if self.window.store.get(item["id"])["packet"]["sheet"] != item["sheet"]:
                raise ValueError("Fresh-process SQLite read differs")
        target = self.expected["shadow"]
        self.load_history(self.window, lambda: actions.on_historial(self.window), target["id"])
        if self.window.invent_sheet != target["sheet"]:
            raise ValueError("Shadow history recovery differs")
        self.snapshot("shadow-recovered", self.window)
        if os.environ.get("CRIBA_ACCEPTANCE_SHADOW_ONLY") == "1":
            self.report.update(
                status="REAL_SHADOW_RESTART_PASS",
                new_model_requests=0,
                identities={"shadow": target["id"]},
            )
            self.finish(0)
            return
        self.blackforge = BlackforgeWindow(database=str(self.home / "criba.sqlite3"))
        self.blackforge.show()
        target = self.expected["blackforge"]
        self.load_history(
            self.blackforge, lambda: self.blackforge._select_navigation("history"), target["id"]
        )
        if self.blackforge.invent_sheet != target["sheet"]:
            raise ValueError("BLACKFORGE history recovery differs")
        self.snapshot("blackforge-recovered", self.blackforge)
        self.report.update(
            status="REAL_INVENTION_RESTART_PASS",
            new_model_requests=0,
            identities={k: v["id"] for k, v in self.expected.items()},
        )
        self.finish(0)

    def fail(self, exc):
        self.report.update(
            status="REAL_INVENTION_FAIL",
            stage=self.stage,
            error_kind=type(exc).__name__,
            error=f"{type(exc).__name__}: {exc}",
            traceback=traceback.format_exc()[-2500:],
        )
        self.finish(3)

    def finish(self, code):
        self.stage = "FINISHED"
        self.timer.stop()
        self.report["elapsed_s"] = round(time.monotonic() - self.started, 2)
        (self.directory / (self.mode + "-report.json")).write_text(
            json.dumps(self.report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if self.blackforge is not None:
            if self.blackforge._proposal_dialog is not None:
                self.blackforge._proposal_dialog.close()
            self.blackforge.close()
        self.window.close()
        self.app.exit(code)
