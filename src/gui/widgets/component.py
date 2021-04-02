import logging

from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QFont
from PySide2.QtWidgets import (QAction, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QSpacerItem, QStyle, QVBoxLayout,
                               QWidget)

gLogger = logging.getLogger(f"edobot.{__name__}")


class ComponentWidget(QWidget):
    removeClicked = Signal(str)

    def __init__(self, id: str, name: str, description: str) -> None:
        super().__init__()

        self.id = id
        self.name = name
        self.description = name

        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

        self.horizontal_layout = QHBoxLayout()

        self.vertical_layout = QVBoxLayout()

        self.label_name = QLabel(name, self)
        font = QFont()
        font.setPointSize(20)
        self.label_name.setFont(font)
        self.label_name.setAlignment(Qt.AlignmentFlag.AlignBottom |  # type: ignore
                                     Qt.AlignmentFlag.AlignLeading |
                                     Qt.AlignmentFlag.AlignLeft)
        self.vertical_layout.addWidget(self.label_name)

        self.label_description = QLabel(description, self)
        self.label_description.setAlignment(Qt.AlignmentFlag.AlignTop |  # type: ignore
                                            Qt.AlignmentFlag.AlignLeading |
                                            Qt.AlignmentFlag.AlignLeft)
        self.vertical_layout.addWidget(self.label_description)

        self.horizontal_layout.addLayout(self.vertical_layout)

        self.horizontal_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.horizontal_layout.addItem(self.horizontal_spacer)

        self.remove_button = QPushButton(self)
        self.remove_button.setFlat(True)
        self.remove_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.remove_button.clicked.connect(self.remove_requested)  # type: ignore
        self.horizontal_layout.addWidget(self.remove_button)

        # self.retranslateUi()
        self.create_actions()

        self.setLayout(self.horizontal_layout)

        # QMetaObject.connectSlotsByName(self)

    def remove_requested(self):
        self.removeClicked.emit(self.id)  # type: ignore

    def create_actions(self):
        action = QAction("Copy", self)
        action.setStatusTip("Copy the selected items")
        action.triggered.connect(self.copy_selection)  # type: ignore
        self.addAction(action)

    def copy_selection(self):
        print("HOLA")

    # def retranslateUi(self):
        # self.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        # self.label.setText(QCoreApplication.translate("Form", u"TextLabel", None))
        # self.pushButton.setText(QCoreApplication.translate("Form", u"Settings", None))
        # self.checkBox.setText(QCoreApplication.translate("Form", u"Enabled", None))
