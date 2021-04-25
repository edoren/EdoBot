import os.path
from typing import Optional

from PySide2.QtCore import QCoreApplication, QFile, Qt, Signal
from PySide2.QtGui import QIntValidator, QShowEvent
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from core.constants import Constants


class SettingsWidget(QWidget):
    accountHostConnectPressed = Signal()
    accountBotConnectPressed = Signal()
    accountHostDisconnectPressed = Signal()
    accountBotDisconnectPressed = Signal()
    obsWebsocketSettingsChanged = Signal(dict)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)

        self.setWindowTitle(self.__get_translation("Settings"))
        self.overrideWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint |  # type: ignore
                                 Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        file = QFile(os.path.join(Constants.DATA_DIRECTORY, "designer", "settings.ui"))
        file.open(QFile.OpenModeFlag.ReadOnly)  # type: ignore
        my_widget = QUiLoader().load(file, self)
        file.close()

        self.host_account_info_label = getattr(my_widget, "host_account_info_label")
        self.host_account_label: QLabel = getattr(my_widget, "host_account_label")
        self.host_account_button: QPushButton = getattr(my_widget, "host_account_button")
        self.bot_account_info_label = getattr(my_widget, "bot_account_info_label")
        self.bot_account_label: QLabel = getattr(my_widget, "bot_account_label")
        self.bot_account_button: QPushButton = getattr(my_widget, "bot_account_button")
        self.host_line_edit: QLineEdit = getattr(my_widget, "host_line_edit")
        self.port_line_edit: QLineEdit = getattr(my_widget, "port_line_edit")
        self.password_line_edit: QLineEdit = getattr(my_widget, "password_line_edit")

        self.port_line_edit.setValidator(QIntValidator(0, 2**16 - 1, self))
        self.host_account_info_label.setText(self.host_account_info_label.text() + ":")
        self.bot_account_info_label.setText(self.bot_account_info_label.text() + ":")

        # Connect signals
        self.host_line_edit.editingFinished.connect(self.obs_config_changed)  # type: ignore
        self.port_line_edit.editingFinished.connect(self.obs_config_changed)  # type: ignore
        self.password_line_edit.editingFinished.connect(self.obs_config_changed)  # type: ignore
        self.set_host_account(None)
        self.set_bot_account(None)

        layout = QVBoxLayout()
        layout.addWidget(my_widget)
        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())

    def obs_config_changed(self):
        self.obsWebsocketSettingsChanged.emit({  # type: ignore
            "host": self.host_line_edit.text(),
            "port": int(self.port_line_edit.text()),
            "password": self.password_line_edit.text()
        })

    def set_host_account(self, name: Optional[str]):
        try:
            self.host_account_button.clicked.disconnect()  # type: ignore
        except Exception:
            pass
        if name:
            self.host_account_label.setText(name)
            self.host_account_label.setStyleSheet("QLabel {  color: black; }")
            self.host_account_button.setText(self.__get_translation("Disconnect"))
            self.host_account_button.clicked.connect(self.accountHostDisconnectPressed.emit)  # type: ignore
        else:
            self.host_account_label.setText(self.__get_translation("Not Connected"))
            self.host_account_label.setStyleSheet("QLabel {  color: gray; }")
            self.host_account_button.setText(self.__get_translation("Connect"))
            self.host_account_button.clicked.connect(self.accountHostConnectPressed.emit)  # type: ignore
        self.host_account_button.setDisabled(False)

    def set_bot_account(self, name: Optional[str]):
        try:
            self.bot_account_button.clicked.disconnect()  # type: ignore
        except Exception:
            pass
        if name:
            self.bot_account_label.setText(name)
            self.bot_account_label.setStyleSheet("QLabel {  color: black; }")
            self.bot_account_button.setText(self.__get_translation("Disconnect"))
            self.bot_account_button.clicked.connect(self.accountBotDisconnectPressed.emit)  # type: ignore
        else:
            self.bot_account_label.setText(self.__get_translation("Not Connected"))
            self.bot_account_label.setStyleSheet("QLabel {  color: gray; }")
            self.bot_account_button.setText(self.__get_translation("Connect"))
            self.bot_account_button.clicked.connect(self.accountBotConnectPressed.emit)  # type: ignore
        self.bot_account_button.setDisabled(False)

    def showEvent(self, event: QShowEvent) -> None:
        r = self.parentWidget().geometry()
        self.setGeometry(r.left() + int((r.width() - self.width()) / 2),
                         r.top() + int((r.height() - self.height()) / 2), self.width(), self.height())
        event.accept()

    def __get_translation(self, value: str) -> str:
        return QCoreApplication.translate("Settings", value, None)  # type: ignore
