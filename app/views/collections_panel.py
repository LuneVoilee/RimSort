from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.models.collections import Collection


class CollectionListWidget(QListWidget):
    collection_selected_signal = Signal(str)
    collection_open_requested_signal = Signal(str)
    add_package_ids_to_collection_signal = Signal(str, list)

    def __init__(self) -> None:
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.currentItemChanged.connect(self._on_current_item_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def _collection_id_from_item(self, item: QListWidgetItem | None) -> str | None:
        if item is None:
            return None
        collection_id = item.data(Qt.ItemDataRole.UserRole)
        return collection_id if isinstance(collection_id, str) else None

    def _on_current_item_changed(
        self, current: QListWidgetItem | None, previous: QListWidgetItem | None
    ) -> None:
        del previous
        collection_id = self._collection_id_from_item(current)
        if collection_id:
            self.collection_selected_signal.emit(collection_id)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        collection_id = self._collection_id_from_item(item)
        if collection_id:
            self.collection_open_requested_signal.emit(collection_id)

    def get_selected_collection_id(self) -> str | None:
        return self._collection_id_from_item(self.currentItem())

    def dropEvent(self, event: QDropEvent) -> None:
        source = event.source()
        if source is None or not hasattr(source, "get_selected_package_ids"):
            event.ignore()
            return

        drop_position = event.position().toPoint()
        target_item = self.itemAt(drop_position)
        collection_id = self._collection_id_from_item(target_item)
        if not collection_id:
            event.ignore()
            return

        package_ids = source.get_selected_package_ids()
        if not package_ids:
            event.ignore()
            return

        event.setDropAction(Qt.DropAction.CopyAction)
        self.add_package_ids_to_collection_signal.emit(collection_id, package_ids)
        event.accept()


class CollectionsPanel(QWidget):
    create_collection_requested_signal = Signal()
    edit_collection_requested_signal = Signal(str)
    rename_collection_requested_signal = Signal(str)
    delete_collection_requested_signal = Signal(str)
    sort_collection_requested_signal = Signal(str)
    export_collection_requested_signal = Signal(str)
    add_package_ids_to_collection_signal = Signal(str, list)
    collection_selected_signal = Signal(str)
    collection_open_requested_signal = Signal(str)
    back_to_collection_list_signal = Signal()

    def __init__(self) -> None:
        super().__init__()

        self._detail_widget: QWidget | None = None

        self.panel = QVBoxLayout()

        self.collections_label = QLabel(self.tr("Collections [0]"))
        self.collections_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.collections_label.setObjectName("summaryValue")
        self.panel.addWidget(self.collections_label)

        self.stack = QStackedWidget()
        self.panel.addWidget(self.stack)

        self.list_page = QWidget()
        self.list_page_layout = QVBoxLayout()
        self.collections_list = CollectionListWidget()
        self.list_page_layout.addWidget(self.collections_list)
        self.list_page.setLayout(self.list_page_layout)

        self.detail_page = QWidget()
        self.detail_page_layout = QVBoxLayout()
        self.detail_toolbar_layout = QGridLayout()
        self.back_button = QPushButton(self.tr("Back"))
        self.detail_title_label = QLabel(self.tr("Collection"))
        self.detail_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_title_label.setObjectName("summaryValue")
        self.sort_button = QPushButton(self.tr("Sort"))
        self.export_button = QPushButton(self.tr("Export"))

        self.left_toolbar_widget = QWidget()
        self.left_toolbar_layout = QHBoxLayout()
        self.left_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.left_toolbar_layout.addWidget(self.back_button)
        self.left_toolbar_layout.addStretch()
        self.left_toolbar_widget.setLayout(self.left_toolbar_layout)

        self.right_toolbar_widget = QWidget()
        self.right_toolbar_layout = QHBoxLayout()
        self.right_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.right_toolbar_layout.addStretch()
        self.right_toolbar_layout.addWidget(self.sort_button)
        self.right_toolbar_layout.addWidget(self.export_button)
        self.right_toolbar_widget.setLayout(self.right_toolbar_layout)

        self.detail_toolbar_layout.setColumnStretch(0, 1)
        self.detail_toolbar_layout.setColumnStretch(1, 1)
        self.detail_toolbar_layout.setColumnStretch(2, 1)
        self.detail_toolbar_layout.addWidget(self.left_toolbar_widget, 0, 0)
        self.detail_toolbar_layout.addWidget(
            self.detail_title_label,
            0,
            1,
            Qt.AlignmentFlag.AlignCenter,
        )
        self.detail_toolbar_layout.addWidget(self.right_toolbar_widget, 0, 2)
        self.detail_page_layout.addLayout(self.detail_toolbar_layout)
        self.detail_list_container = QWidget()
        self.detail_list_layout = QVBoxLayout()
        self.detail_list_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_list_container.setLayout(self.detail_list_layout)
        self.detail_page_layout.addWidget(self.detail_list_container)
        self.detail_page.setLayout(self.detail_page_layout)

        self.stack.addWidget(self.list_page)
        self.stack.addWidget(self.detail_page)
        self.stack.setCurrentWidget(self.list_page)

        self.collections_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.setLayout(self.panel)
        self._connect_signals()

    def _connect_signals(self) -> None:
        self.collections_list.customContextMenuRequested.connect(
            self._show_list_context_menu
        )
        self.export_button.clicked.connect(self._emit_export_requested)
        self.sort_button.clicked.connect(self._emit_sort_requested)
        self.back_button.clicked.connect(self._on_back_clicked)

        self.collections_list.collection_selected_signal.connect(
            self.collection_selected_signal.emit
        )
        self.collections_list.collection_open_requested_signal.connect(
            self.collection_open_requested_signal.emit
        )
        self.collections_list.add_package_ids_to_collection_signal.connect(
            self.add_package_ids_to_collection_signal.emit
        )

    def attach_detail_widget(self, widget: QWidget) -> None:
        if self._detail_widget is not None:
            self.detail_list_layout.removeWidget(self._detail_widget)
            self._detail_widget.setParent(None)
        self._detail_widget = widget
        self.detail_list_layout.addWidget(widget)

    def selected_collection_id(self) -> str | None:
        current = self.collections_list.currentItem()
        if current is None:
            return None
        collection_id = current.data(Qt.ItemDataRole.UserRole)
        return collection_id if isinstance(collection_id, str) else None

    def set_collections(
        self, collections: list[Collection], selected_collection_id: str | None = None
    ) -> None:
        current_selection = selected_collection_id or self.selected_collection_id()
        self.collections_list.clear()
        selected_row = -1

        for index, collection in enumerate(collections):
            item = QListWidgetItem(
                self.tr("{name} [{count}]").format(
                    name=collection.name, count=len(collection.package_ids)
                )
            )
            item.setData(Qt.ItemDataRole.UserRole, collection.id)
            self.collections_list.addItem(item)
            if collection.id == current_selection:
                selected_row = index

        if selected_row >= 0:
            self.collections_list.setCurrentRow(selected_row)
        elif self.collections_list.count() > 0:
            self.collections_list.setCurrentRow(0)

        self.collections_label.setText(
            self.tr("Collections [{count}]").format(count=len(collections))
        )

    def set_detail_title(self, title: str) -> None:
        self.detail_title_label.setText(title)

    def show_collection_list(self) -> None:
        self.stack.setCurrentWidget(self.list_page)

    def show_collection_detail(self) -> None:
        self.stack.setCurrentWidget(self.detail_page)

    def _on_back_clicked(self) -> None:
        self.show_collection_list()
        self.back_to_collection_list_signal.emit()

    def _emit_rename_requested(self) -> None:
        collection_id = self.selected_collection_id()
        if collection_id:
            self.rename_collection_requested_signal.emit(collection_id)

    def _emit_edit_requested(self) -> None:
        collection_id = self.selected_collection_id()
        if collection_id:
            self.edit_collection_requested_signal.emit(collection_id)

    def _emit_delete_requested(self) -> None:
        collection_id = self.selected_collection_id()
        if collection_id:
            self.delete_collection_requested_signal.emit(collection_id)

    def _emit_sort_requested(self) -> None:
        collection_id = self.selected_collection_id()
        if collection_id:
            self.sort_collection_requested_signal.emit(collection_id)

    def _emit_export_requested(self) -> None:
        collection_id = self.selected_collection_id()
        if collection_id:
            self.export_collection_requested_signal.emit(collection_id)

    def _show_list_context_menu(self, position: QPoint) -> None:
        clicked_item = self.collections_list.itemAt(position)
        if clicked_item is not None:
            self.collections_list.setCurrentItem(clicked_item)

        menu = QMenu(self)
        new_action = menu.addAction(self.tr("New"))
        edit_action = None
        delete_action = None

        if self.selected_collection_id():
            edit_action = menu.addAction(self.tr("Edit"))
            delete_action = menu.addAction(self.tr("Delete"))

        action = menu.exec(self.collections_list.viewport().mapToGlobal(position))
        if action == new_action:
            self.create_collection_requested_signal.emit()
        elif action == edit_action:
            self._emit_edit_requested()
        elif action == delete_action:
            self._emit_delete_requested()
