"""Plain proposal presentation shared by the existing desktop interfaces."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from criba.interprete.diagnostico import CRITIQUE_REJECTED


def format_proposal(entry: dict[str, Any], position: int = 1, total: int = 1) -> str:
    """Show the idea and mechanism, not the internal JSON or self-assessment."""
    sections = [f"Propuesta {position} de {total}"]
    if entry.get("estado_interpretacion") != "PROPUESTA":
        diagnostic = entry.get("interpretacion_diagnostico")
        rejected = (
            isinstance(diagnostic, dict)
            and diagnostic.get("error_code") == CRITIQUE_REJECTED
        )
        sections.append(
            "PROPUESTA RECHAZADA" if rejected else "PENDIENTE DE INTERPRETACIÓN"
        )
        sections.append(
            "MOTIVO\n" + str(entry.get("interpretacion_error") or "sin motivo declarado")
        )
        route = entry.get("ruta_desbloqueo")
        if route:
            sections.append("RUTA DE DESBLOQUEO\n" + str(route))
        if isinstance(diagnostic, dict) and diagnostic:
            code = str(diagnostic.get("error_code") or "").strip()
            phase = str(diagnostic.get("phase") or "").strip()
            http_status = diagnostic.get("http_status")
            retryable = diagnostic.get("retryable")
            next_action = str(diagnostic.get("next_action") or "").strip()
            detail = [
                f"Código: {code}" if code else "",
                f"Fase: {phase}" if phase else "",
                f"HTTP: {http_status}" if http_status is not None else "",
                (
                    "Reintentable: sí" if retryable else "Reintentable: no"
                ) if retryable is not None else "",
                f"Siguiente acción: {next_action}" if next_action else "",
            ]
            detail = [part for part in detail if part]
            if detail:
                sections.append("DIAGNÓSTICO\n" + "\n".join(detail))
        if rejected:
            critica = entry.get("critica")
            respuesta = critica.get("respuesta") if isinstance(critica, dict) else None
            objeciones = respuesta.get("objeciones") if isinstance(respuesta, dict) else None
            if isinstance(objeciones, list):
                items = [str(item).strip() for item in objeciones if str(item).strip()]
                if items:
                    sections.append(
                        "OBJECIONES\n" + "\n".join(f"- {item}" for item in items)
                    )
        return "\n\n".join(sections)
    sections.extend(
        (
            "QUÉ SE PROPONE\n" + str(entry.get("hipotesis") or "No declarado"),
            "CÓMO FUNCIONARÍA\n" + str(entry.get("mecanismo") or "No declarado"),
            "Propuesta creativa; novedad, viabilidad y eficacia no comprobadas.",
        )
    )
    uncertainty = str(entry.get("incertidumbre") or "").strip()
    if uncertainty:
        sections.append("QUÉ FALTA COMPROBAR\n" + uncertainty)
    return "\n\n".join(sections)


class ProposalResultsDialog(QDialog):
    """Read, navigate and preserve proposals with the common history store."""

    def __init__(
        self, sheet: dict[str, Any], store: Any, parent: Any = None, selected_index: int = 0
    ) -> None:
        super().__init__(parent)
        self.sheet, self.store = sheet, store
        self.entries = list(sheet.get("entries", []))
        self.index = max(0, min(selected_index, len(self.entries) - 1))
        self.saved_indices: set[int] = set()
        self.setWindowTitle("Propuestas · " + str(sheet.get("query") or "")[:90])
        self.resize(760, 570)
        layout = QVBoxLayout(self)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)
        row = QHBoxLayout()
        self.previous = QPushButton("←")
        self.following = QPushButton("→")
        self.position = QLabel()
        self.previous.clicked.connect(lambda: self.show_entry(self.index - 1))
        self.following.clicked.connect(lambda: self.show_entry(self.index + 1))
        row.addWidget(self.previous)
        row.addWidget(self.position)
        row.addWidget(self.following)
        row.addStretch()
        self.save_button = QPushButton("Guardar propuesta")
        self.save_button.clicked.connect(self.save_current)
        row.addWidget(self.save_button)
        layout.addLayout(row)
        self.advanced = QCheckBox("Modo avanzado: técnicas, procedencia y diagnóstico")
        self.advanced.toggled.connect(lambda _checked: self.show_entry(self.index))
        layout.addWidget(self.advanced)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.show_entry(self.index)

    def show_entry(self, index: int) -> None:
        if not self.entries:
            self.output.setPlainText("No hay propuestas en esta sesión.")
            self.save_button.setEnabled(False)
            self.previous.setEnabled(False)
            self.following.setEnabled(False)
            return
        self.index = max(0, min(index, len(self.entries) - 1))
        entry = self.entries[self.index]
        text = format_proposal(entry, self.index + 1, len(self.entries))
        if self.advanced.isChecked():
            import json

            text += "\n\nDATOS AVANZADOS\n" + json.dumps(entry, ensure_ascii=False, indent=2)
        self.output.setPlainText(text)
        self.position.setText(f"{self.index + 1} / {len(self.entries)}")
        self.previous.setEnabled(self.index > 0)
        self.following.setEnabled(self.index < len(self.entries) - 1)
        self.save_button.setEnabled(
            entry.get("estado_interpretacion") == "PROPUESTA"
            and bool(str(entry.get("mecanismo") or "").strip())
            and self.index not in self.saved_indices
        )

    def save_current(self) -> None:
        try:
            ident = self.store.save_invention(self.sheet, selected_index=self.index)
            recovered = self.store.get(ident)["packet"]
            if recovered["sheet"] != self.sheet or recovered["selected_index"] != self.index:
                raise ValueError("La lectura posterior no coincide con la propuesta.")
        except Exception as exc:
            self.status.setText(f"Guardado no confirmado: {type(exc).__name__}")
            return
        self.saved_indices.add(self.index)
        self.saved_id = ident
        self.save_button.setEnabled(False)
        self.status.setText("Propuesta y cruce completo guardados en el historial.")
