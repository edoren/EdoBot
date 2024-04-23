import logging
import os.path
import time
from typing import Any, List, Mapping, MutableMapping, Optional, Set, Union

import qtawesome as qta
from PySide6.QtCore import QCoreApplication, QFile, QRegularExpression, QSize, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from edobot.core import Component
from edobot.model import EventType, User, UserType

__all__ = ["CommandsComponent"]

gLogger = logging.getLogger("edobot.components.commands")


class CommandsTableWidget(QWidget):
    def __init__(self, data_parent: "CommandsComponent") -> None:
        super().__init__()

        self.data_parent = data_parent

        file = QFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ui"))
        file.open(QFile.OpenModeFlag.ReadOnly)  # type: ignore
        my_widget = QUiLoader().load(file, self)
        file.close()

        file = QFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "add_command.ui"))
        file.open(QFile.OpenModeFlag.ReadOnly)  # type: ignore
        self.edit_dialog: QDialog = QUiLoader().load(file, self)  # type: ignore
        file.close()

        self.table_widget: QTableWidget = getattr(my_widget, "table_widget")
        self.add_command_button: QPushButton = getattr(my_widget, "add_command_button")

        self.editing_command = None
        self.edit_dialog_command_input: QLineEdit = getattr(self.edit_dialog, "command_input")
        self.edit_dialog_response_input: QPlainTextEdit = getattr(self.edit_dialog, "response_input")
        self.edit_dialog_cooldown_input: QSpinBox = getattr(self.edit_dialog, "cooldown_input")
        self.edit_dialog_user_cooldown_input: QSpinBox = getattr(self.edit_dialog, "user_cooldown_input")
        self.edit_dialog_access_level_input: QComboBox = getattr(self.edit_dialog, "access_level_input")
        self.edit_dialog_button_box: QDialogButtonBox = getattr(self.edit_dialog, "button_box")

        self.access_levels = {
            UserType.CHATTER: QCoreApplication.translate("Commands", "Chatter", None),
            UserType.SUBSCRIPTOR: QCoreApplication.translate("Commands", "Subscriber", None),
            UserType.VIP: QCoreApplication.translate("Commands", "VIP", None),
            UserType.MODERATOR: QCoreApplication.translate("Commands", "Moderator", None),
            UserType.EDITOR: QCoreApplication.translate("Commands", "Editor", None),
            UserType.BROADCASTER: QCoreApplication.translate("Commands", "Broadcaster", None),
        }

        self.table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.edit_dialog_command_input.setValidator(QRegularExpressionValidator(QRegularExpression("[a-z-A-Z0-9_]+")))
        for key, value in self.access_levels.items():
            self.edit_dialog_access_level_input.addItem(value, key)
        self.setMinimumWidth(my_widget.width())

        self.edit_dialog_button_box.accepted.connect(self.edit_accepted)  # type: ignore
        self.edit_dialog_button_box.rejected.connect(self.edit_dialog.reject)  # type: ignore
        self.add_command_button.clicked.connect(self.add_command_button_clicked)  # type: ignore

        layout = QVBoxLayout()
        layout.addWidget(my_widget)
        self.setLayout(layout)

        # Fill with the initial data
        for comm in self.data_parent.commands:
            row_pos = self.table_widget.rowCount()
            access_level = None
            for user_type in UserType:
                if isinstance(comm["access_level"], str) and comm["access_level"].lower() == user_type.name.lower():
                    access_level = user_type
                elif isinstance(comm["access_level"], int) and comm["access_level"] == user_type.value:
                    access_level = user_type
            if access_level is not None:
                self.table_widget.insertRow(row_pos)
                self.add_command(
                    row_pos,
                    comm["enabled"],
                    comm["command"],
                    comm["response"],
                    comm["cooldown"],
                    comm["user_cooldown"],
                    access_level,
                )

    def add_command_button_clicked(self):
        self.edit_dialog.setWindowTitle("New Command")
        self.editing_command = None
        self.edit_dialog_command_input.setText("")
        self.edit_dialog_response_input.setPlainText("")
        self.edit_dialog_cooldown_input.setValue(0)
        self.edit_dialog_user_cooldown_input.setValue(0)
        self.edit_dialog_access_level_input.setCurrentIndex(0)
        self.edit_dialog.show()

    def edit_button_clicked(self, command: str):
        self.edit_dialog.setWindowTitle(f"Editing Command: {command}")
        row = self.find_command_row(command)
        if row is None:
            return
        self.edit_dialog_command_input.setText(self.table_widget.item(row, 1).text())
        self.edit_dialog_response_input.setPlainText(self.table_widget.item(row, 2).text())
        self.edit_dialog_cooldown_input.setValue(int(self.table_widget.item(row, 3).text()))
        self.edit_dialog_user_cooldown_input.setValue(int(self.table_widget.item(row, 4).text()))
        access_level_data: UserType = self.table_widget.item(row, 5).data(Qt.UserRole)  # type: ignore
        index = self.edit_dialog_access_level_input.findData(access_level_data)
        self.edit_dialog_access_level_input.setCurrentIndex(index)
        self.editing_command = command
        self.edit_dialog.show()

    def delete_button_clicked(self, command: str):
        row = self.find_command_row(command)
        if row is not None:
            self.table_widget.removeRow(row)
        self.data_parent.store_commands(self.create_save_data())

    def edit_accepted(self):
        command_text = self.edit_dialog_command_input.text().lower()
        response_text = self.edit_dialog_response_input.toPlainText()
        cooldown_value = self.edit_dialog_cooldown_input.value()
        user_cooldown_value = self.edit_dialog_user_cooldown_input.value()
        access_level_key: UserType = self.edit_dialog_access_level_input.currentData()

        if not command_text or not response_text:
            QMessageBox.critical(self.edit_dialog, "Error", "Please fill all required data.")
            return

        found_row = self.find_command_row(command_text)

        row_pos = None
        if self.editing_command is None:  # If adding a new command
            if found_row is None:
                row_pos = self.table_widget.rowCount()
                self.table_widget.insertRow(row_pos)
        else:  # If edditing a command
            if self.editing_command == command_text and found_row is not None:  # If not renaming
                row_pos = found_row
            elif self.editing_command != command_text and found_row is None:  # If renaming
                row_pos = self.find_command_row(self.editing_command)

        if row_pos is None:
            QMessageBox.critical(self.edit_dialog, "Error", f"Command '{command_text}' already exists.")
            return

        self.add_command(
            row_pos, True, command_text, response_text, cooldown_value, user_cooldown_value, access_level_key
        )

        self.edit_dialog.accept()
        self.data_parent.store_commands(self.create_save_data())

    def add_command(
        self,
        row: int,
        enabled: bool,
        command: str,
        response: str,
        cooldown: int,
        user_cooldown: int,
        access_level_key: UserType,
    ):
        self.table_widget.setSortingEnabled(False)
        enabled_cb = QCheckBox()
        enabled_cb.setChecked(enabled)
        enabled_cb.clicked.connect(lambda _: self.data_parent.store_commands(self.create_save_data()))  # type: ignore
        self.table_widget.setCellWidget(row, 0, enabled_cb)  # Enabled
        self.table_widget.setItem(row, 1, QTableWidgetItem(command))  # Command
        self.table_widget.setItem(row, 2, QTableWidgetItem(response))  # Response
        self.table_widget.setItem(row, 3, QTableWidgetItem(str(cooldown)))  # Cooldown
        self.table_widget.setItem(row, 4, QTableWidgetItem(str(user_cooldown)))  # User Cooldown
        access_level_item = QTableWidgetItem(self.access_levels[access_level_key])
        access_level_item.setData(Qt.UserRole, access_level_key)  # type: ignore
        self.table_widget.setItem(row, 5, access_level_item)  # Access Level
        delete_button_widget = QWidget()
        delete_button = QToolButton()
        delete_button.setIcon(qta.icon("fa5s.trash"))
        delete_button.setIconSize(QSize(20, 20))
        delete_button.setMinimumSize(36, 36)
        delete_button.clicked.connect(lambda _: self.delete_button_clicked(command))  # type: ignore
        delete_button_layout = QHBoxLayout(delete_button_widget)
        delete_button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore
        delete_button_layout.setContentsMargins(0, 5, 5, 5)
        delete_button_layout.addWidget(delete_button)
        self.table_widget.setCellWidget(row, 6, delete_button_widget)  # Delete
        edit_button_widget = QWidget()
        edit_button = QToolButton()
        edit_button.setIcon(qta.icon("fa5s.edit"))
        edit_button.setIconSize(QSize(20, 20))
        edit_button.setMinimumSize(36, 36)
        edit_button.clicked.connect(lambda _: self.edit_button_clicked(command))  # type: ignore
        edit_button_layout = QHBoxLayout(edit_button_widget)
        edit_button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore
        edit_button_layout.setContentsMargins(5, 5, 0, 5)
        edit_button_layout.addWidget(edit_button)
        self.table_widget.setCellWidget(row, 7, edit_button_widget)  # Edit
        self.table_widget.setSortingEnabled(True)

    def find_command_row(self, command: str) -> Optional[int]:
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, 1)  # Command
            if item.text() == command:
                return row

    def create_save_data(self) -> List[Mapping[str, Any]]:
        result: List[Mapping[str, Any]] = []
        for row in range(self.table_widget.rowCount()):
            result.append(
                {
                    "enabled": self.table_widget.cellWidget(row, 0).isChecked(),  # type: ignore
                    "command": self.table_widget.item(row, 1).text(),
                    "response": self.table_widget.item(row, 2).text(),
                    "cooldown": int(self.table_widget.item(row, 3).text()),
                    "user_cooldown": int(self.table_widget.item(row, 4).text()),
                    "access_level": self.table_widget.item(row, 5).data(Qt.UserRole).value,  # type: ignore
                }
            )
        return result


class CommandsComponent(Component):  # TODO: Change to chat store
    def __init__(self) -> None:
        super().__init__()
        # command_name: last_called_time
        self.cooldown_times: MutableMapping[str, Optional[int]] = {}
        # user: {command_name: last_called_time}
        self.user_cooldown_times: MutableMapping[str, MutableMapping[str, Optional[int]]] = {}

    @staticmethod
    def get_id() -> str:
        return "commands"

    @staticmethod
    def get_metadata() -> Component.Metadata:
        return Component.Metadata(
            name=QCoreApplication.translate("Commands", "Commands", None),
            description=QCoreApplication.translate("Commands", "Add custom commands to interact with the chat", None),
            icon=qta.icon("fa5.list-alt"),
        )

    def start(self) -> None:
        self.commands = self.config["commands"].get([])
        return super().start()

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return None  # To get all the messages without command filtering

    def process_message(
        self, message: str, user: User, user_types: Set[UserType], metadata: Optional[Any] = None
    ) -> None:
        if not message.startswith("!"):
            return

        parts = message[1:].split(" ")
        if len(parts) > 0:
            command = parts[0].lower()
            for cmd in self.commands:
                is_enabled = cmd["enabled"]
                user_type = UserType(cmd["access_level"])
                current_time = round(time.time() * 1000)
                if is_enabled and user_type in user_types and cmd["command"] == command:
                    global_cooldown_time = self.cooldown_times.get(command)
                    user_cooldown_time = self.user_cooldown_times.setdefault(user.login, {}).get(command)
                    if (global_cooldown_time is None or global_cooldown_time < current_time) and (
                        user_cooldown_time is None or user_cooldown_time < current_time
                    ):
                        self.cooldown_times[command] = current_time + (cmd["cooldown"] * 1000)
                        self.user_cooldown_times[user.login][command] = current_time + (cmd["user_cooldown"] * 1000)
                        self.chat.send_message(cmd["response"])
                    # else:
                    #     if global_cooldown_time:
                    #         print("Global cooldown:", global_cooldown_time - current_time)
                    #     if user_cooldown_time:
                    #         print("User cooldown:", user_cooldown_time - current_time)

    def process_event(self, event_type: EventType, metadata: Any) -> None:
        pass

    def get_config_ui(self) -> Optional[QWidget]:
        return CommandsTableWidget(self)

    def store_commands(self, save_data):
        self.commands = save_data
        self.config["commands"] = save_data
