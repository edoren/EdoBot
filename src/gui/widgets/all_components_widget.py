import json
from typing import Optional

from PySide2.QtCore import QByteArray, QMimeData, Qt
from PySide2.QtWidgets import QLabel, QListWidget, QListWidgetItem, QWidget

from core.chat_component import ChatComponent

from .base_list_widget import BaseListWidget


class AllComponentsWidget(BaseListWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet("QListWidget::item { background: transparent; }\n"
                           "QListWidget::item:hover { background: rgba(0,0,0,0.2); }")
        # self.setStyleSheet("QListWidget::item:hover,\n"
        #                    "QListWidget::item:disabled,\n"
        #                    "QListWidget::item:disabled:hover,\n"
        #                    "QListWidget::item:hover:!active\n"
        #                    "{ background: transparent; }")
        # self.setStyleSheet("QListWidget::item:selected { background: rgb(128,128,255); }")
        # self.log_widget.model().rowsInserted.connect(self.log_widget.scrollToBottom)  # type: ignore

    def startDrag(self, supportedActions: Qt.DropActions) -> None:
        drag, painter, pixmap = self.start_drag_base()
        components = [item.data(Qt.UserRole) for item in self.selectedItems()]  # type: ignore
        mime_data = QMimeData()
        mime_data.setData("application/x-edobotcomponent", QByteArray(json.dumps(components).encode("UTF-8")))
        drag.setMimeData(mime_data)
        drag.exec_(supportedActions, Qt.DropAction.MoveAction)
        del painter
        del pixmap

    def add_component(self, meta: ChatComponent.Metadata):
        widget = QLabel(meta.name)
        widget.setStyleSheet("QLabel { padding: 0 5px 0 5px; }")
        widget.setFixedHeight(20)
        widget.setToolTip(meta.description)
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, {"id": meta.id})  # type: ignore
        item.setSizeHint(widget.sizeHint())
        item.setIcon(meta.icon)
        self.addItem(item)
        self.setItemWidget(item, widget)
