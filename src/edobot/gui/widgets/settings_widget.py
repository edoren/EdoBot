import os.path
import winreg
from typing import Optional

from PySide6.QtCore import QCoreApplication, QFile, QSettings, Qt, Signal
from PySide6.QtGui import QIntValidator, QShowEvent
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from edobot.core.constants import Constants


class SettingsWidget(QWidget):
    accountHostConnectPressed = Signal()
    accountBotConnectPressed = Signal()
    accountHostDisconnectPressed = Signal()
    accountBotDisconnectPressed = Signal()
    systemTrayEnabled = Signal(bool)
    obsConfigChanged = Signal(dict)

    def __init__(self, parent: QWidget, app_settings: QSettings) -> None:
        super().__init__(parent=parent)

        self.app_settings = app_settings

        self.setWindowTitle(self.tr("Settings"))
        self.overrideWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint  # type: ignore
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
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
        self.obs_choice_combo_box: QComboBox = getattr(my_widget, "obs_choice_combo_box")
        self.host_line_edit: QLineEdit = getattr(my_widget, "host_line_edit")
        self.port_line_edit: QLineEdit = getattr(my_widget, "port_line_edit")
        self.password_line_edit: QLineEdit = getattr(my_widget, "password_line_edit")
        self.system_startup_check_box: QCheckBox = getattr(my_widget, "system_startup_check_box")
        self.system_tray_check_box: QCheckBox = getattr(my_widget, "system_tray_check_box")

        # Set config and default values
        self.port_line_edit.setValidator(QIntValidator(0, 2**16 - 1, self))
        self.host_account_info_label.setText(self.host_account_info_label.text() + ":")
        self.bot_account_info_label.setText(self.bot_account_info_label.text() + ":")
        self.obs_choice_combo_box.addItem("OBS WebSocket", "obswebsocket")
        self.obs_choice_combo_box.addItem("Streamlabs OBS", "slobs")
        self.system_startup_check_box.setChecked(self.is_open_on_startup_enabled())  # type: ignore
        self.system_tray_check_box.setChecked(self.is_system_tray_enabled())  # type: ignore

        # Debug overrides
        if not Constants.IS_FROZEN:
            self.system_startup_check_box.setEnabled(False)

        # Connect signals
        self.host_line_edit.editingFinished.connect(self.obs_config_changed)  # type: ignore
        self.port_line_edit.editingFinished.connect(self.obs_config_changed)  # type: ignore
        self.password_line_edit.editingFinished.connect(self.obs_config_changed)  # type: ignore
        self.system_startup_check_box.stateChanged.connect(  # type: ignore
            lambda state: self.open_on_startup_enabled_changed(state == Qt.CheckState.Checked)
        )
        self.system_tray_check_box.stateChanged.connect(  # type: ignore
            lambda state: self.system_tray_enabled_changed(state == Qt.CheckState.Checked)
        )
        self.set_host_account(None)
        self.set_bot_account(None)

        layout = QVBoxLayout()
        layout.addWidget(my_widget)
        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())

    def obs_config_changed(self):
        self.obsConfigChanged.emit(
            {  # type: ignore
                "host": self.host_line_edit.text(),
                "port": int(self.port_line_edit.text()),
                "password": self.password_line_edit.text(),
            }
        )

    def set_host_account(self, name: Optional[str]):
        try:
            self.host_account_button.clicked.disconnect()  # type: ignore
        except Exception:
            pass
        if name:
            self.host_account_label.setText(name)
            self.host_account_label.setStyleSheet("QLabel {  color: black; }")
            self.host_account_button.setText(self.tr("Disconnect"))
            self.host_account_button.clicked.connect(self.accountHostDisconnectPressed.emit)  # type: ignore
        else:
            self.host_account_label.setText(self.tr("Not Connected"))
            self.host_account_label.setStyleSheet("QLabel {  color: gray; }")
            self.host_account_button.setText(self.tr("Connect"))
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
            self.bot_account_button.setText(self.tr("Disconnect"))
            self.bot_account_button.clicked.connect(self.accountBotDisconnectPressed.emit)  # type: ignore
        else:
            self.bot_account_label.setText(self.tr("Not Connected"))
            self.bot_account_label.setStyleSheet("QLabel {  color: gray; }")
            self.bot_account_button.setText(self.tr("Connect"))
            self.bot_account_button.clicked.connect(self.accountBotConnectPressed.emit)  # type: ignore
        self.bot_account_button.setDisabled(False)

    def is_system_tray_enabled(self) -> bool:
        return self.app_settings.value("system_tray", True, bool)  # type: ignore

    def is_open_on_startup_enabled(self) -> bool:
        if not Constants.IS_FROZEN:
            return False
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_READ
            ) as registry_key:
                # TODO: Check same executable
                value, regtype = winreg.QueryValueEx(registry_key, "EdoBot")  # type: ignore
            return True
        except WindowsError:
            return False

    def system_tray_enabled_changed(self, enabled: bool):
        self.app_settings.setValue("system_tray", enabled)
        self.systemTrayEnabled.emit(enabled)  # type: ignore

    def open_on_startup_enabled_changed(self, enabled: bool):
        if not Constants.IS_FROZEN:
            return
        try:
            reg_path = R"Software\Microsoft\Windows\CurrentVersion\Run"
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE) as registry_key:
                if enabled:
                    run_in_bg_cmd = f"\"{os.path.join(Constants.EXECUTABLE_DIRECTORY, 'edobot.exe')}\" --background"
                    winreg.SetValueEx(registry_key, "EdoBot", 0, winreg.REG_SZ, run_in_bg_cmd)
                else:
                    winreg.DeleteValue(registry_key, "EdoBot")
        except WindowsError:
            pass

    def showEvent(self, event: QShowEvent) -> None:
        r = self.parentWidget().geometry()
        self.setGeometry(
            r.left() + int((r.width() - self.width()) / 2),
            r.top() + int((r.height() - self.height()) / 2),
            self.width(),
            self.height(),
        )
        event.accept()
