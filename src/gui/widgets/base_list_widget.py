from typing import Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor, QDrag, QPainter, QPixmap
from PySide6.QtWidgets import QListWidget


class BaseListWidget(QListWidget):

    def startDrag(self, supportedActions: Qt.DropActions) -> None:
        drag, painter, pixmap = self.start_drag_base()
        drag.exec_(supportedActions, Qt.DropAction.MoveAction)
        del painter
        del pixmap

    def start_drag_base(self) -> Tuple[QDrag, QPainter, QPixmap]:
        drag = QDrag(self)
        drag.setMimeData(self.model().mimeData(self.selectedIndexes()))
        pixmap = QPixmap(self.viewport().visibleRegion().boundingRect().size())
        pixmap.fill(QColor(Qt.GlobalColor.transparent))
        painter = QPainter(pixmap)
        for index in self.selectedIndexes():  # type: ignore
            painter.drawPixmap(self.visualRect(index), self.viewport().grab(self.visualRect(index)))
        drag.setPixmap(pixmap)
        drag.setHotSpot(self.viewport().mapFromGlobal(QCursor.pos()))
        return drag, painter, pixmap
