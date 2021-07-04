import logging
import os.path
from datetime import datetime
from typing import Any, List, Optional, Set, Union

import qtawesome as qta
from PySide2.QtCore import QFile, QUrl
from PySide2.QtGui import QDesktopServices
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QFileDialog, QWidget

from core import ChatComponent
from model import User, UserType

__all__ = ["ChatStoreComponent"]

gLogger = logging.getLogger("edobot.components.chat_store")


class ChatStoreComponent(ChatComponent):
    def __init__(self) -> None:
        super().__init__()
        self.widget: Optional[QWidget] = None

    @staticmethod
    def get_metadata() -> ChatComponent.Metadata:
        return ChatComponent.Metadata(id="chat_store", name="Chat Store",
                                      description="Stores the chat in a specific folder",
                                      icon=qta.icon("fa5s.database"))

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return None  # To get all the messages without command filtering

    def start(self) -> None:
        self.filename = ~self.config["filename"]
        if self.filename is None or not isinstance(self.filename, str):
            self.filename = "edobot-{date}"
            self.config["filename"] = self.filename
        self.filedir = ~self.config["filedir"]
        if self.filedir is None or not isinstance(self.filedir, str):
            self.filedir = os.path.expanduser("~")
            self.config["filedir"] = self.filedir
        self.ignored_users = ~self.config["ignored_users"]
        if self.ignored_users is None or not isinstance(self.ignored_users, list):
            self.ignored_users = ["streamelements", "streamlabs"]
            self.config["ignored_users"] = self.ignored_users
        super().start()

    def stop(self) -> None:
        super().stop()

    def process_message(self, message: str, user: User, user_types: Set[UserType],
                        metadata: Optional[Any] = None) -> None:
        full_filename = self.filename.replace("{date}", datetime.now().strftime('%d-%m-%Y'))
        for username in self.ignored_users:
            if username.lower() == user.login:
                return
        if not full_filename.endswith(".txt"):
            full_filename += ".txt"
        with open(os.path.join(self.filedir, full_filename), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [{user.display_name}] {message}\n")

    def process_event(self, event_name: str, metadata: Any) -> None:
        pass

    def get_config_something(self) -> Optional[QWidget]:
        file = QFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_store.ui"))
        file.open(QFile.OpenModeFlag.ReadOnly)  # type: ignore
        self.widget = QUiLoader().load(file)
        file.close()

        self.filename_line_edit = getattr(self.widget, "filename_line_edit")
        self.filedir_line_edit = getattr(self.widget, "filedir_line_edit")
        self.select_folder_button = getattr(self.widget, "select_folder_button")
        self.open_folder_button = getattr(self.widget, "open_folder_button")
        self.ignored_users_line_edit = getattr(self.widget, "ignored_users_line_edit")

        self.ignored_users_line_edit.setText(", ".join(self.ignored_users))
        self.filename_line_edit.setText(self.filename)
        self.filedir_line_edit.setText(self.filedir)

        self.ignored_users_line_edit.editingFinished.connect(self.ignored_users_changed)
        self.filename_line_edit.editingFinished.connect(self.filename_changed)
        self.select_folder_button.clicked.connect(self.select_folder)
        self.open_folder_button.clicked.connect(self.open_folder)

        return self.widget

    # Slots
    def filename_changed(self):
        self.filename = self.filename_line_edit.text().strip()
        self.config["filename"] = self.filename

    def select_folder(self):
        filedir = QFileDialog.getExistingDirectory(None, "Select Output Folder", self.filedir)
        if filedir:
            self.filedir = os.path.normpath(filedir)
            self.config["filedir"] = self.filedir
            self.filedir_line_edit.setText(self.filedir)

    def open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.filedir_line_edit.text()))

    def ignored_users_changed(self):
        self.ignored_users = self.ignored_users_line_edit.text().strip().replace(" ", "").split(",")
        self.config["ignored_users"] = self.ignored_users
