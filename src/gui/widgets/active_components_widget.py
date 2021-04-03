import json
from typing import Optional

from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide2.QtWidgets import QListWidget, QListWidgetItem, QWidget

from .all_components_widget import AllComponentsWidget
from .base_list_widget import BaseListWidget
from .component_widget import ComponentWidget


class ActiveComponentsWidget(BaseListWidget):
    componentClicked = Signal(str)
    componentDropped = Signal(str)
    componentRemoved = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAlternatingRowColors(True)
        self.setAcceptDrops(True)
        self.currentItemChanged.connect(self.component_clicked)  # type: ignore
        # self.setStyleSheet("QListWidget::item { border-bottom: 1px solid black; }")

    def add_component(self, widget: ComponentWidget):
        for i in range(self.count()):
            item = self.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)  # type: ignore
            if data["id"] == widget.id:
                return
        widget.removeClicked.connect(self.remove_component)  # type: ignore
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, {"id": widget.id})  # type: ignore
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)

    def remove_component(self, component_id: str):
        for i in range(self.count()):
            item = self.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)  # type: ignore
            if data["id"] == component_id:
                self.takeItem(i)
                self.componentRemoved.emit(component_id)  # type: ignore
                return

    def component_clicked(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        data = current_item.data(Qt.ItemDataRole.UserRole)  # type: ignore
        self.componentClicked.emit(data["id"])  # type: ignore

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.accept()

    def dragMoveEvent(self, e: QDragMoveEvent) -> None:
        e.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        mimeData = event.mimeData()
        if isinstance(event.source(), self.__class__):
            event.setDropAction(Qt.DropAction.MoveAction)
            super().dropEvent(event)
        if isinstance(event.source(), AllComponentsWidget):
            bdata = mimeData.data("application/x-edobotcomponent")
            components = json.loads(bdata.data().decode("UTF-8"))
            for component in components:
                self.componentDropped.emit(component["id"])  # type: ignore
        event.accept()
