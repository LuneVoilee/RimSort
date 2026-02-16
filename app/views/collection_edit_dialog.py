from __future__ import annotations

import re

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.collections import DEFAULT_COLLECTION_COLOR


class CollectionEditDialog(QDialog):
    def __init__(
        self,
        name: str,
        description: str,
        color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Edit Collection"))

        self.name_input = QLineEdit(name)
        self.description_input = QTextEdit()
        self.description_input.setPlainText(description)
        self.description_input.setMinimumHeight(180)

        self.color_input = QLineEdit(color or DEFAULT_COLLECTION_COLOR)
        self.pick_color_button = QPushButton(self.tr("Pick"))
        self.pick_color_button.clicked.connect(self._pick_color)

        color_layout = QHBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.addWidget(self.color_input)
        color_layout.addWidget(self.pick_color_button)

        form_layout = QFormLayout()
        form_layout.addRow(self.tr("Name:"), self.name_input)
        form_layout.addRow(self.tr("Description:"), self.description_input)
        form_layout.addRow(self.tr("Color:"), color_layout)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @staticmethod
    def tr(text: str) -> str:
        return QCoreApplication.translate("CollectionEditDialog", text)

    def _pick_color(self) -> None:
        current = QColor(self.color_input.text().strip())
        if not current.isValid():
            current = QColor(DEFAULT_COLLECTION_COLOR)
        chosen = QColorDialog.getColor(current, self, self.tr("Select color"))
        if chosen.isValid():
            self.color_input.setText(chosen.name())

    def _on_accept(self) -> None:
        color_text = self.color_input.text().strip().lower()
        if not re.fullmatch(r"#[0-9a-f]{6}", color_text):
            self.color_input.setText(DEFAULT_COLLECTION_COLOR)
        self.accept()

    def values(self) -> tuple[str, str, str]:
        return (
            self.name_input.text().strip(),
            self.description_input.toPlainText().strip(),
            self.color_input.text().strip().lower(),
        )
