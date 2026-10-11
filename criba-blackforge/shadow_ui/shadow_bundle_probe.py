"""Opt-in bundled Windows acceptance probe.

Runs only in an isolated temporary profile via verify_shadow_windows.py.
Exercises *packaged* Qt widgets, real deterministic CRIBA, HTTP SUPRA,
disk state and a second process restore. Never uses a mocked transport,
pretends a screenshot is a human visual review, or activates BLACKFORGE.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import traceback
import urllib.request
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QImage


PROBLEM = "Reducir errores de registros de almacén sin aumentar tiempos de inspección."
MAX_RUNTIME_S = 150.0


def verify_rendered_image(window: Any, destination: Path) -> dict[str, Any]:
    """Widget painting evidence; never a claim of physical desktop visibility."""
    window.repaint()
    picture = window.grab()
    if picture.isNull() or picture.width() < 900 or picture.height() < 600:
        raise RuntimeError("Qt did not paint an adequately sized main window")
    image = picture.toImage().convertToFormat(QImage.Format.Format_RGB32)
    colors: set[int] = set()
    for row in range(5, image.height(), max(1, image.height() // 17)):
        for col in range(5, image.width(), max(1, image.width() // 31)):
            colors.add(int(image.pixel(col, row)))
    if len(colors) < 14:
        raise RuntimeError(f"Screen surface looks blank or monotone ({len(colors)} sampled colors)")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not picture.save(str(destination), "PNG"):
        raise RuntimeError("Qt grab PNG could not be written")
    payload = destination.read_bytes()
    if len(payload) < 10000:
        raise RuntimeError(f"Suspiciously small Qt screenshot ({len(payload)} bytes)")
    return {
        "source": "QWidget.grab (Qt paint buffer, not independent screen capture)",
        "width": picture.width(), "height": picture.height(),
        "sampled_distinct_colors": len(colors),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "desktop_visual_acceptance": "NOT_VERIFIED",
    }


def restored_provenance_is_honest(summary: str) -> bool:
    """Accept a disk GET OR a truthful cache GET with the durable copy checked.

    SUPRA's LIST can warm the cache before the subsequent GET during reload;
    after restart the authoritative path is still tested against the disk
    artifact. Reject claims that mislabel cache as direct disk provenance.
    """
    if "Resultado PREVIO recuperado mediante GET" not in summary:
        return False
    if "la caché del proceso SUPRA" in summary:
        return "copia durable verificada contra la caché" in summary
    if "el estado persistido" in summary:
        return "copia durable verificada desde el artefacto" in summary
    return False


def _read_project(endpoint: str, project_id: str) -> dict[str, Any]:
    url = endpoint.rstrip("/") + "/api/v1/projects/" + project_id
    with urllib.request.urlopen(url, timeout=8) as response:
        if response.status != 200:
            raise RuntimeError(f"SUPRA read returned {response.status}")
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("posture"), dict):
        raise RuntimeError("SUPRA GET did not return project posture")
    return payload


class BundleProbe(QObject):
    def __init__(self, app: Any, window: Any, home: Path, mode: str) -> None:
        super().__init__(window)
        self.app, self.window, self.home, self.mode = app, window, home, mode
        self.stage = "START"
        self.started = time.monotonic()
        self.report: dict[str, Any] = {
            "mode": mode, "status": "IN_PROGRESS",
            "transport": "REAL_HTTP", "app": "PACKAGED_EXE",
            "model_calls": "NONE_REQUIRED", "scientific_advantage": "NOT_ESTABLISHED",
            "desktop_visual_acceptance": "NOT_VERIFIED",
        }
        self.directory = home / "bundle-verification"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.timer = QTimer(self)
        self.timer.setInterval(180)
        self.timer.timeout.connect(self.poll)
        QTimer.singleShot(350, self.begin)

    def screenshot(self, kind: str) -> None:
        self.report[f"image_{kind}"] = verify_rendered_image(
            self.window, self.directory / f"shadow-{self.mode}-{kind}.png"
        )

    def begin(self) -> None:
        try:
            self.screenshot("initial")
            if self.mode == "journey":
                self.window.header.problem_input.setText(PROBLEM)
                self.window.header.problem_input.returnPressed.emit()
                if self.window.problem != PROBLEM:
                    raise RuntimeError("header submit did not update the canonical CRIBA problem")
                if not self.window.topcards.btn_gen.isEnabled():
                    raise RuntimeError("real Generate button is not enabled after problem submission")
                self.window.topcards.btn_gen.click()
                self.stage = "GENERATE"
            elif self.mode == "restore":
                self.stage = "RESTORE"
            else:
                raise ValueError("unsupported probe mode")
            self.timer.start()
        except Exception as exc:
            self.fail(exc)

    def poll(self) -> None:
        try:
            if time.monotonic() - self.started > MAX_RUNTIME_S:
                raise TimeoutError(f"Bundle probe timed out in {self.stage}")
            if self.window.errorBanner.isVisibleTo(self.window):
                raise RuntimeError(
                    f"UI error in {self.stage}: {self.window.errorBannerText.text()}"
                )
            if self.stage == "GENERATE":
                packet = self.window.packet
                if packet is None or getattr(self.window, "_live_workers", []):
                    return
                ideas = packet.get("innovation", {}).get("ideas", [])
                if not ideas:
                    raise RuntimeError("CRIBA deterministic core generated zero ideas")
                self.report["generated_ideas"] = len(ideas)
                self.screenshot("generated")
                button = self.window.right_panel.supra_e2e
                if not button.isEnabled() or not button.isVisibleTo(self.window):
                    raise RuntimeError("SUPRA dispatch button not active/visible in actual window")
                button.click()
                self.stage = "SUPRA_POST_GET"
            elif self.stage == "SUPRA_POST_GET":
                if getattr(self.window, "_live_workers", []):
                    return
                title = self.window.refs["ideaTitle"].text()
                if not title.startswith("SUPRA astram2"):
                    raise RuntimeError(f"SUPRA button did not render real GET result: {title!r}")
                project_id = title.removeprefix("SUPRA ").strip()
                self.validate_project(project_id, restoring=False)
                self.screenshot("supra")
                self.complete()
            elif self.stage == "RESTORE":
                project_id = os.environ.get("CRIBASHADOW_EXPECTED_PROJECT_ID", "")
                if not project_id:
                    raise RuntimeError("expected project ID missing in isolated restore phase")
                if getattr(self.window, "_live_workers", []):
                    return
                title = self.window.refs["ideaTitle"].text()
                if title != f"SUPRA recuperado · {project_id}":
                    raise RuntimeError(f"Second process did not restore the actual project: {title!r}")
                summary = self.window.refs["ideaSummary"].text()
                if not restored_provenance_is_honest(summary):
                    raise RuntimeError(f"UI failed to report restored provenance: {summary}")
                self.validate_project(project_id, restoring=True)
                self.screenshot("restored")
                self.complete()
        except Exception as exc:
            self.fail(exc)

    def status_on_screen(self) -> bool:
        scroller = getattr(self.window, "candidates_scroll", None)
        label = self.window.refs["ideaTitle"]
        if scroller is None or not label.isVisibleTo(self.window):
            return False
        point = label.mapTo(scroller.viewport(), label.rect().center())
        return bool(scroller.viewport().rect().contains(point))

    def validate_project(self, project_id: str, *, restoring: bool) -> None:
        if not project_id.startswith("astram2"):
            raise RuntimeError("project id not issued by canonical M2 flow")
        endpoint = os.environ.get("SUPRA_ENDPOINT", "")
        data = _read_project(endpoint, project_id)
        posture = data["posture"]
        receipt = posture.get("criba_dossier_receipt")
        if not isinstance(receipt, dict):
            raise RuntimeError("real GET omitted planning receipt")
        if receipt.get("execution_status") != "NOT_EXECUTED":
            raise RuntimeError("planning receipt falsely claims execution")
        if receipt.get("scientific_status") != "NOT_VALIDATED":
            raise RuntimeError("planning receipt falsely claims scientific verification")
        path = self.home / "supra_state" / f"{project_id}.json"
        if not path.is_file() or path.stat().st_size < 100:
            raise RuntimeError("durable SUPRA state artifact not found")
        if restoring:
            summary = self.window.candidates.supra_output.toPlainText()
            if project_id not in summary:
                raise RuntimeError("restored project not rendered in SUPRA panel")
        else:
            if not self.window.refs["ideaEstadoChip"].isVisibleTo(self.window):
                raise RuntimeError("SUPRA status chip is hidden from actual UI")
        self.report["project_id"] = project_id
        self.report["http_get_status"] = 200
        self.report["artifact_exists"] = True
        self.report["receipt_execution_status"] = receipt["execution_status"]
        self.report["receipt_scientific_status"] = receipt["scientific_status"]
        self.report["ui_status_visible"] = self.window.refs["ideaEstadoChip"].isVisibleTo(self.window)
        self.report["status_in_viewport"] = self.status_on_screen()
        if not self.report["status_in_viewport"]:
            raise RuntimeError("SUPRA status rendered but outside the visible scroll viewport")
        side_status = self.window.right_panel.supra_result_status
        expected_mode = "SUPRA previo:" if restoring else "SUPRA actual:"
        if expected_mode not in side_status.text() or "NOT_VALIDATED" not in side_status.text():
            raise RuntimeError(f"right-panel status missing real SUPRA GET facts: {side_status.text()}")
        area = self.window.right_panel_scroll
        point = side_status.mapTo(area.viewport(), side_status.rect().center())
        self.report["side_status_in_viewport"] = area.viewport().rect().contains(point)
        if not self.report["side_status_in_viewport"]:
            raise RuntimeError("SUPRA right-panel status is outside the visible viewport")
        self.report["provenance_source"] = data.get("status_source", "UNKNOWN")

    def complete(self) -> None:
        self.report["status"] = "BUNDLED_JOURNEY_PASS" if self.mode == "journey" else "BUNDLED_RESTORE_PASS"
        self.finish(0)

    def fail(self, exc: BaseException) -> None:
        self.report["status"] = "BUNDLED_JOURNEY_FAIL"
        self.report["failure_stage"] = self.stage
        self.report["error"] = f"{type(exc).__name__}: {exc}"
        self.report["traceback"] = traceback.format_exc()[-2200:]
        try:
            self.screenshot("failure")
        except Exception:
            pass
        self.finish(3)

    def finish(self, exit_code: int) -> None:
        self.timer.stop()
        self.report["elapsed_s"] = round(time.monotonic() - self.started, 2)
        target = self.directory / f"{self.mode}-report.json"
        target.write_text(json.dumps(self.report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.app.exit(exit_code)


def start_bundle_probe(app: Any, window: Any, home: Path, mode: str) -> BundleProbe:
    """Refuse external/mutable user data: this is *only* an isolated CI test."""
    if (home.name != "isolated-state"
            or not home.parent.name.startswith("criba-shadow-release-")
            or os.environ.get("CRIBASHADOW_HOME") != str(home)):
        raise RuntimeError("Bundled probe refuses any non-temporary user-data directory")
    probe = BundleProbe(app, window, home, mode)
    window._bundle_probe = probe
    return probe
