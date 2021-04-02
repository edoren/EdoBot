import logging
from typing import Optional

from PySide2.QtCore import QCoreApplication, QSize, Qt, Signal
from PySide2.QtGui import QCloseEvent, QFont, QIntValidator, QShowEvent
from PySide2.QtWidgets import (QFormLayout, QGridLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout, QWidget)

gLogger = logging.getLogger(f"edobot.{__name__}")


class SettingsWidget(QWidget):
    accountHostConnectPressed = Signal()
    accountBotConnectPressed = Signal()
    accountHostDisconnectPressed = Signal()
    accountBotDisconnectPressed = Signal()
    obsWebsocketSettingsChanged = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)

        self.setObjectName("Settings")

        self.resize(350, 250)
        self.setFixedSize(QSize(350, 250))
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setObjectName("verticalLayout")
        self.edobot_group_box = QGroupBox(self)
        self.edobot_group_box.setObjectName("groupBox")
        self.verticalLayout_3 = QVBoxLayout(self.edobot_group_box)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.bot_account_info_label = QLabel(self.edobot_group_box)
        self.bot_account_info_label.setObjectName("label_2")

        self.gridLayout.addWidget(self.bot_account_info_label, 1, 0, 1, 1)

        font = QFont()
        font.setBold(True)
        font.setWeight(75)

        self.host_account_status_label = QLabel(self.edobot_group_box)
        self.host_account_status_label.setObjectName("account_status_label")
        self.host_account_status_label.setFont(font)

        self.gridLayout.addWidget(self.host_account_status_label, 0, 2, 1, 1)

        self.bot_account_status_label = QLabel(self.edobot_group_box)
        self.bot_account_status_label.setObjectName("bot_account_status_label")
        self.bot_account_status_label.setFont(font)

        self.gridLayout.addWidget(self.bot_account_status_label, 1, 2, 1, 1)

        self.host_account_info_label = QLabel(self.edobot_group_box)
        self.host_account_info_label.setObjectName("label")

        self.gridLayout.addWidget(self.host_account_info_label, 0, 0, 1, 1)

        self.host_account_label = QLabel(self.edobot_group_box)
        self.host_account_label.setObjectName("account_label")
        self.host_account_label.setFont(font)

        self.gridLayout.addWidget(self.host_account_label, 0, 1, 1, 1)

        self.bot_account_label = QLabel(self.edobot_group_box)
        self.bot_account_label.setObjectName("bot_account_label")
        self.bot_account_label.setFont(font)

        self.gridLayout.addWidget(self.bot_account_label, 1, 1, 1, 1)

        self.verticalLayout_3.addLayout(self.gridLayout)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.host_account_button = QPushButton(self.edobot_group_box)
        self.host_account_button.setObjectName("host_account_button")

        self.horizontalLayout.addWidget(self.host_account_button)

        self.bot_account_button = QPushButton(self.edobot_group_box)
        self.bot_account_button.setObjectName("bot_account_button")

        self.horizontalLayout.addWidget(self.bot_account_button)

        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.verticalLayout.addWidget(self.edobot_group_box)

        self.obs_websocket_group_box = QGroupBox(self)
        self.obs_websocket_group_box.setObjectName("groupBox_2")
        self.verticalLayout_4 = QVBoxLayout(self.obs_websocket_group_box)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.formLayout_2 = QFormLayout()
        self.formLayout_2.setObjectName("formLayout_2")

        self.port_label = QLabel(self.obs_websocket_group_box)
        self.port_label.setObjectName("port_label")
        self.formLayout_2.setWidget(1, QFormLayout.ItemRole.LabelRole, self.port_label)

        self.password_line_edit = QLineEdit(self.obs_websocket_group_box)
        self.password_line_edit.setObjectName("password_line_edit")
        self.password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.FieldRole, self.password_line_edit)

        self.port_line_edit = QLineEdit(self.obs_websocket_group_box)
        self.port_line_edit.setObjectName("port_line_edit")
        self.port_line_edit.setInputMethodHints(Qt.InputMethodHint.ImhDigitsOnly)  # type: ignore
        self.port_line_edit.setValidator(QIntValidator(0, 2**16-1, self))
        self.formLayout_2.setWidget(1, QFormLayout.ItemRole.FieldRole, self.port_line_edit)

        self.password_label = QLabel(self.obs_websocket_group_box)
        self.password_label.setObjectName("password_label")
        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.LabelRole, self.password_label)

        self.host_label = QLabel(self.obs_websocket_group_box)
        self.host_label.setObjectName("host_label")
        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.LabelRole, self.host_label)

        self.host_line_edit = QLineEdit(self.obs_websocket_group_box)
        self.host_line_edit.setObjectName("host_line_edit")
        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.FieldRole, self.host_line_edit)

        self.verticalLayout_4.addLayout(self.formLayout_2)

        self.verticalLayout.addWidget(self.obs_websocket_group_box)

        self.retranslate_ui()

        # Connect signals
        self.obs_config_changed_flag = False
        self.host_line_edit.textEdited.connect(self.obs_config_changed)  # type: ignore
        self.port_line_edit.textEdited.connect(self.obs_config_changed)  # type: ignore
        self.password_line_edit.textEdited.connect(self.obs_config_changed)  # type: ignore
        self.set_host_account(None)
        self.set_bot_account(None)

    def retranslate_ui(self):
        self.setWindowTitle(self.get_translation("Form"))
        self.edobot_group_box.setTitle(self.get_translation("EdoBot"))
        self.bot_account_info_label.setText(self.get_translation("Bot Account:"))
        self.host_account_status_label.setText(self.get_translation("Disconnected"))
        self.bot_account_status_label.setText(self.get_translation("Disconnected"))
        self.host_account_info_label.setText(self.get_translation("Account:"))
        self.host_account_label.setText(self.get_translation("Name"))
        self.bot_account_label.setText(self.get_translation("Name"))
        self.host_account_button.setText(self.get_translation("Connect Host"))
        self.bot_account_button.setText(self.get_translation("Connect Bot"))
        self.obs_websocket_group_box.setTitle(self.get_translation("OBS Websocket"))
        self.port_label.setText(self.get_translation("Port"))
        self.password_label.setText(self.get_translation("Password"))
        self.host_label.setText(self.get_translation("Host"))

    def obs_config_changed(self):
        self.obs_config_changed_flag = True

    def set_host_account(self, name: Optional[str]):
        try:
            self.host_account_button.clicked.disconnect()  # type: ignore
        except Exception:
            pass
        if name:
            self.host_account_label.setText(name)
            self.host_account_status_label.setText(self.get_translation("Connected"))
            self.host_account_button.setText("Disconnect Host")
            self.host_account_button.clicked.connect(self.accountHostDisconnectPressed.emit)  # type: ignore
        else:
            self.host_account_label.setText("")
            self.host_account_status_label.setText(self.get_translation("Disconnected"))
            self.host_account_button.setText(self.get_translation("Connect Host"))
            self.host_account_button.clicked.connect(self.accountHostConnectPressed.emit)  # type: ignore
        self.host_account_button.setDisabled(False)

    def set_bot_account(self, name: Optional[str]):
        try:
            self.bot_account_button.clicked.disconnect()  # type: ignore
        except Exception:
            pass
        if name:
            self.bot_account_label.setText(name)
            self.bot_account_status_label.setText(self.get_translation("Connected"))
            self.bot_account_button.setText(self.get_translation("Disconnect Bot"))
            self.bot_account_button.clicked.connect(self.accountBotDisconnectPressed.emit)  # type: ignore
        else:
            self.bot_account_label.setText("")
            self.bot_account_status_label.setText(self.get_translation("Disconnected"))
            self.bot_account_button.setText(self.get_translation("Connect Bot"))
            self.bot_account_button.clicked.connect(self.accountBotConnectPressed.emit)  # type: ignore
        self.bot_account_button.setDisabled(False)

    def showEvent(self, event: QShowEvent) -> None:
        self.obs_config_changed_flag = False
        event.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.obs_config_changed_flag:
            self.obsWebsocketSettingsChanged.emit({  # type: ignore
                "host": self.host_line_edit.text(),
                "port": int(self.port_line_edit.text()),
                "password": self.password_line_edit.text()
            })
        event.accept()

    def get_translation(self, value: str) -> str:
        return QCoreApplication.translate("Settings", value, None)  # type: ignore
