import json
from typing import Optional

from PySide6.QtCore import QByteArray, QMimeData, Qt
from PySide6.QtWidgets import QAbstractItemView, QLabel, QListWidgetItem, QWidget

from edobot.core.component import Component

from .base_list_widget import BaseListWidget

__all__ = ["AllComponentsWidget"]


class AllComponentsWidgetItem(QListWidgetItem):
    def __init__(self, id: str, meta: Component.Metadata):
        super().__init__()
        self.widget = QLabel(meta.name)
        self.widget.setStyleSheet("QLabel { padding: 0 5px 0 5px; }")
        self.widget.setFixedHeight(20)
        self.widget.setToolTip(meta.description)
        self.setData(Qt.ItemDataRole.UserRole, {"id": id, "name": meta.name})  # type: ignore
        self.setSizeHint(self.widget.sizeHint())
        self.setIcon(meta.icon)

    def __lt__(self, other: "AllComponentsWidgetItem"):
        data = self.data(Qt.ItemDataRole.UserRole)  # type: ignore
        other_data = other.data(Qt.ItemDataRole.UserRole)  # type: ignore
        return data["name"] < other_data["name"]


class AllComponentsWidget(BaseListWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSortingEnabled(True)
        self.setStyleSheet(
            "QListWidget::item { background: transparent; }\n"
            "QListWidget::item:hover { background: rgba(0,0,0,0.2); }"
        )
        # self.setStyleSheet("QListWidget::item:hover,\n"
        #                    "QListWidget::item:disabled,\n"
        #                    "QListWidget::item:disabled:hover,\n"
        #                    "QListWidget::item:hover:!active\n"
        #                    "{ background: transparent; }")
        # self.setStyleSheet("QListWidget::item:selected { background: rgb(128,128,255); }")
        # self.log_widget.model().rowsInserted.connect(self.log_widget.scrollToBottom)  # type: ignore

    def startDrag(self, supportedActions: Qt.DropAction) -> None:
        drag, painter, pixmap = self.start_drag_base()
        components = [item.data(Qt.UserRole) for item in self.selectedItems()]  # type: ignore
        mime_data = QMimeData()
        mime_data.setData("application/x-edobotcomponent", QByteArray(json.dumps(components).encode("UTF-8")))
        drag.setMimeData(mime_data)
        drag.exec_(supportedActions, Qt.DropAction.MoveAction)
        del painter
        del pixmap

    def add_component(self, id: str, meta: Component.Metadata):
        item = AllComponentsWidgetItem(id, meta)
        self.addItem(item)
        self.setItemWidget(item, item.widget)
