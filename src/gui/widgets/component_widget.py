import os.path

from PySide2.QtCore import QFile, Signal
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QLabel, QPushButton, QStyle, QVBoxLayout, QWidget

from core.constants import Constants


class ComponentWidget(QWidget):
    removeClicked = Signal(str)

    def __init__(self, id: str, name: str, description: str) -> None:
        super().__init__()

        self.id = id
        self.name = name
        self.description = description

        file = QFile(os.path.join(Constants.DATA_DIRECTORY, "designer", "component.ui"))
        file.open(QFile.OpenModeFlag.ReadOnly)  # type: ignore
        my_widget = QUiLoader().load(file, self)
        file.close()

        self.remove_button: QPushButton = getattr(my_widget, "remove_button")
        self.label_name: QLabel = getattr(my_widget, "label_name")
        self.label_description: QLabel = getattr(my_widget, "label_description")

        self.label_name.setText(self.name)
        self.label_description.setText(self.description)
        self.remove_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))

        # Connect signals
        self.remove_button.clicked.connect(self.remove_requested)  # type: ignore

        layout = QVBoxLayout()
        layout.addWidget(my_widget)
        self.setLayout(layout)

    def remove_requested(self):
        self.removeClicked.emit(self.id)  # type: ignore
