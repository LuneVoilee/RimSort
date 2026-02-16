from __future__ import annotations

import re

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.collections import (
    COLLECTION_COVER_TYPE_AUTO,
    COLLECTION_COVER_TYPE_FILE,
    COLLECTION_COVER_TYPE_PACKAGE,
    DEFAULT_COLLECTION_COLOR,
)


class CollectionEditDialog(QDialog):
    def __init__(
        self,
        name: str,
        description: str,
        color: str,
        cover_type: str = COLLECTION_COVER_TYPE_AUTO,
        cover_image_path: str = "",
        cover_package_id: str = "",
        cover_candidates: list[tuple[str, str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Edit Collection"))
        self.cover_candidates = cover_candidates or []

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

        self.cover_mode_input = QComboBox()
        self.cover_mode_input.addItem(
            self.tr("Auto (last added mod image)"), COLLECTION_COVER_TYPE_AUTO
        )
        self.cover_mode_input.addItem(
            self.tr("Custom uploaded image"), COLLECTION_COVER_TYPE_FILE
        )
        self.cover_mode_input.addItem(
            self.tr("Collection mod image"), COLLECTION_COVER_TYPE_PACKAGE
        )
        initial_cover_type = cover_type if isinstance(cover_type, str) else ""
        normalized_cover_type = initial_cover_type.strip().lower()
        initial_index = self.cover_mode_input.findData(normalized_cover_type)
        if initial_index >= 0:
            self.cover_mode_input.setCurrentIndex(initial_index)

        self.cover_image_path_input = QLineEdit(cover_image_path)
        self.cover_image_path_input.setPlaceholderText(self.tr("No image selected"))
        self.cover_image_browse_button = QPushButton(self.tr("Browse"))
        self.cover_image_browse_button.clicked.connect(self._pick_cover_image)
        self.cover_image_clear_button = QPushButton(self.tr("Clear"))
        self.cover_image_clear_button.clicked.connect(self._clear_cover_image)
        cover_image_layout = QHBoxLayout()
        cover_image_layout.setContentsMargins(0, 0, 0, 0)
        cover_image_layout.addWidget(self.cover_image_path_input)
        cover_image_layout.addWidget(self.cover_image_browse_button)
        cover_image_layout.addWidget(self.cover_image_clear_button)

        self.cover_package_input = QComboBox()
        for package_id, display_name in self.cover_candidates:
            self.cover_package_input.addItem(display_name, package_id)
        if self.cover_package_input.count() == 0:
            self.cover_package_input.addItem(self.tr("No preview images available"), "")
            self.cover_package_input.setEnabled(False)
        if isinstance(cover_package_id, str) and cover_package_id.strip():
            candidate_index = self.cover_package_input.findData(
                cover_package_id.strip().lower()
            )
            if candidate_index >= 0:
                self.cover_package_input.setCurrentIndex(candidate_index)

        self.cover_mode_input.currentIndexChanged.connect(self._update_cover_inputs)

        form_layout = QFormLayout()
        form_layout.addRow(self.tr("Name:"), self.name_input)
        form_layout.addRow(self.tr("Description:"), self.description_input)
        form_layout.addRow(self.tr("Color:"), color_layout)
        form_layout.addRow(self.tr("Cover:"), self.cover_mode_input)
        form_layout.addRow(self.tr("Cover image:"), cover_image_layout)
        form_layout.addRow(self.tr("Cover mod image:"), self.cover_package_input)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.buttons)
        self.setLayout(layout)
        self._update_cover_inputs()

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

    def _pick_cover_image(self) -> None:
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select cover image"),
            "",
            self.tr("Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"),
        )
        if image_path:
            self.cover_image_path_input.setText(image_path)
            index = self.cover_mode_input.findData(COLLECTION_COVER_TYPE_FILE)
            if index >= 0:
                self.cover_mode_input.setCurrentIndex(index)

    def _clear_cover_image(self) -> None:
        self.cover_image_path_input.clear()

    def _update_cover_inputs(self) -> None:
        selected_mode = self.cover_mode_input.currentData()
        mode = selected_mode if isinstance(selected_mode, str) else ""
        is_file_mode = mode == COLLECTION_COVER_TYPE_FILE
        is_package_mode = mode == COLLECTION_COVER_TYPE_PACKAGE

        self.cover_image_path_input.setEnabled(is_file_mode)
        self.cover_image_browse_button.setEnabled(is_file_mode)
        self.cover_image_clear_button.setEnabled(is_file_mode)

        has_package_candidates = len(self.cover_candidates) > 0
        self.cover_package_input.setEnabled(is_package_mode and has_package_candidates)

    def _on_accept(self) -> None:
        color_text = self.color_input.text().strip().lower()
        if not re.fullmatch(r"#[0-9a-f]{6}", color_text):
            self.color_input.setText(DEFAULT_COLLECTION_COLOR)

        selected_mode = self.cover_mode_input.currentData()
        mode = selected_mode if isinstance(selected_mode, str) else ""

        if mode == COLLECTION_COVER_TYPE_FILE:
            if not self.cover_image_path_input.text().strip():
                auto_index = self.cover_mode_input.findData(COLLECTION_COVER_TYPE_AUTO)
                if auto_index >= 0:
                    self.cover_mode_input.setCurrentIndex(auto_index)
        elif mode == COLLECTION_COVER_TYPE_PACKAGE:
            current_package_id = self.cover_package_input.currentData()
            if (
                not isinstance(current_package_id, str)
                or not current_package_id.strip()
                or not self.cover_candidates
            ):
                auto_index = self.cover_mode_input.findData(COLLECTION_COVER_TYPE_AUTO)
                if auto_index >= 0:
                    self.cover_mode_input.setCurrentIndex(auto_index)
        self.accept()

    def values(self) -> tuple[str, str, str, str, str, str]:
        selected_mode = self.cover_mode_input.currentData()
        mode = selected_mode if isinstance(selected_mode, str) else ""
        normalized_mode = mode.strip().lower()

        cover_image_path = ""
        cover_package_id = ""
        if normalized_mode == COLLECTION_COVER_TYPE_FILE:
            cover_image_path = self.cover_image_path_input.text().strip()
            if not cover_image_path:
                normalized_mode = COLLECTION_COVER_TYPE_AUTO
        elif normalized_mode == COLLECTION_COVER_TYPE_PACKAGE:
            current_package_id = self.cover_package_input.currentData()
            if isinstance(current_package_id, str):
                cover_package_id = current_package_id.strip().lower()
            if not cover_package_id:
                normalized_mode = COLLECTION_COVER_TYPE_AUTO
        else:
            normalized_mode = COLLECTION_COVER_TYPE_AUTO

        return (
            self.name_input.text().strip(),
            self.description_input.toPlainText().strip(),
            self.color_input.text().strip().lower(),
            normalized_mode,
            cover_image_path,
            cover_package_id,
        )
