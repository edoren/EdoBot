import logging
import os.path
import time
from typing import Any, List, Optional, Set, Union

import qtawesome as qta
from PySide2.QtCore import QFile, Signal
from PySide2.QtGui import QFocusEvent
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QCheckBox, QComboBox, QLineEdit, QPlainTextEdit, QSpinBox, QWidget

from core import ChatComponent
from model import User, UserType

__all__ = ["AutoShoutOut"]

gLogger = logging.getLogger("edobot.components.auto_shoutout")


class PlainTextEdit(QPlainTextEdit):
    editingFinished = Signal()
    receivedFocus = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._changed = False
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._handle_text_changed)  # type: ignore

    def focusInEvent(self, e: QFocusEvent) -> None:
        super().focusInEvent(e)
        self.receivedFocus.emit()  # type: ignore

    def focusOutEvent(self, e: QFocusEvent) -> None:
        if self._changed:
            self.editingFinished.emit()  # type: ignore
        super().focusInEvent(e)

    def _handle_text_changed(self):
        self._changed = True

    def setTextChanged(self, state=True):
        self._changed = state


class AutoShoutOut(ChatComponent):
    def __init__(self) -> None:
        super().__init__()
        self.widget: Optional[QWidget] = None

    @staticmethod
    def get_metadata() -> ChatComponent.Metadata:
        return ChatComponent.Metadata(id="auto_shoutout", name="Auto Shout-Out",
                                      description="Stores the chat in a specific folder",
                                      icon=qta.icon("fa5s.bullhorn"))

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return None  # To get all the messages without command filtering

    def start(self) -> None:
        self.cooldown = self.config["cooldown"].setdefault(30)
        self.cooldown_format = self.config["cooldown_format"].setdefault("minutes")
        self.blacklist = self.config["blacklist"].setdefault([])
        self.blacklist_enabled = self.config["blacklist_enabled"].setdefault(False)
        self.whitelist = self.config["whitelist"].setdefault([])
        self.whitelist_enabled = self.config["whitelist_enabled"].setdefault(False)
        self.message = self.config["message"].setdefault("")
        self.message_alt = self.config["message_alt"].setdefault("")
        self.last_shoutouts = {}
        super().start()

    def stop(self) -> None:
        super().stop()

    def process_message(self, message: str, user: User, user_types: Set[UserType],
                        metadata: Optional[Any] = None) -> None:
        if self.blacklist_enabled and user.login in self.blacklist:
            return
        if user.broadcaster_type in ("affiliate", "partner") or (self.whitelist_enabled
                                                                 and user.login in self.whitelist):
            current_time = time.time()
            if user.id not in self.last_shoutouts or self.last_shoutouts[user.id] < current_time:
                channel = self.twitch.get_channel(user.id)
                if self.cooldown_format == "hours":
                    added_time = self.cooldown * 3600
                elif self.cooldown_format == "minutes":
                    added_time = self.cooldown * 60
                else:
                    added_time = self.cooldown
                self.last_shoutouts[user.id] = current_time + added_time
                if channel is not None:
                    for message in (self.message, self.message_alt):
                        if message:
                            final_message = message.replace("{name}", user.display_name)
                            final_message = final_message.replace("{game}", channel.game_name)
                            final_message = final_message.replace("{login}", user.login)
                            self.chat.send_message(final_message)

    def process_event(self, event_name: str, metadata: Any) -> None:
        pass

    def get_config_something(self) -> Optional[QWidget]:
        file = QFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ui"))
        file.open(QFile.OpenModeFlag.ReadOnly)  # type: ignore
        loader = QUiLoader()
        loader.registerCustomWidget(PlainTextEdit)
        self.widget = loader.load(file)
        file.close()

        self.cooldown_spin_box: QSpinBox = getattr(self.widget, "cooldown_spin_box")
        self.cooldown_combo_box: QComboBox = getattr(self.widget, "cooldown_combo_box")
        self.message_text_edit: PlainTextEdit = getattr(self.widget, "message_text_edit")
        self.message_alt_text_edit: PlainTextEdit = getattr(self.widget, "message_alt_text_edit")

        self.whitelist_checkbox: QCheckBox = getattr(self.widget, "whitelist_checkbox")
        self.blacklist_checkbox: QCheckBox = getattr(self.widget, "blacklist_checkbox")
        self.whitelist_line_edit: QLineEdit = getattr(self.widget, "whitelist_line_edit")
        self.blacklist_line_edit: QLineEdit = getattr(self.widget, "blacklist_line_edit")

        self.cooldown_spin_box.setValue(self.cooldown)
        self.cooldown_combo_box.addItem("Hours", "hours")
        self.cooldown_combo_box.addItem("Minutes", "minutes")
        self.cooldown_combo_box.addItem("Seconds", "seconds")
        self.cooldown_combo_box.setCurrentIndex(self.cooldown_combo_box.findData(self.cooldown_format))

        self.message_text_edit.setPlainText(self.message)
        self.message_alt_text_edit.setPlainText(self.message_alt)

        self.whitelist_checkbox.setChecked(self.whitelist_enabled)
        self.blacklist_checkbox.setChecked(self.blacklist_enabled)
        self.whitelist_line_edit.setText(", ".join(self.whitelist))
        self.blacklist_line_edit.setText(", ".join(self.blacklist))
        self.whitelist_line_edit.setEnabled(self.whitelist_enabled)
        self.blacklist_line_edit.setEnabled(self.blacklist_enabled)

        self.cooldown_spin_box.valueChanged.connect(self.cooldown_changed)  # type: ignore
        self.cooldown_combo_box.activated.connect(self.cooldown_format_changed)  # type: ignore
        self.message_text_edit.editingFinished.connect(self.message_changed)  # type: ignore
        self.message_alt_text_edit.editingFinished.connect(self.message_alt_changed)  # type: ignore

        self.whitelist_checkbox.stateChanged.connect(self.whitelist_enabled_changed)  # type: ignore
        self.blacklist_checkbox.stateChanged.connect(self.blacklist_enabled_changed)  # type: ignore
        self.whitelist_line_edit.editingFinished.connect(self.whitelist_changed)  # type: ignore
        self.blacklist_line_edit.editingFinished.connect(self.blacklist_changed)  # type: ignore

        return self.widget

    # Slots
    def cooldown_changed(self, value: int):
        self.cooldown = value
        self.config["cooldown"] = self.cooldown

    def cooldown_format_changed(self, index: int):
        self.cooldown_format = self.cooldown_combo_box.itemData(index)
        self.config["cooldown_format"] = self.cooldown_format

    def message_changed(self):
        self.message = self.message_text_edit.toPlainText().replace("\n", "").strip(" ")
        self.config["message"] = self.message

    def message_alt_changed(self):
        self.message_alt = self.message_alt_text_edit.toPlainText().replace("\n", "").strip(" ")
        self.config["message_alt"] = self.message_alt

    def whitelist_enabled_changed(self, state: int):
        self.whitelist_enabled = state != 0
        self.config["whitelist_enabled"] = self.whitelist_enabled
        self.whitelist_line_edit.setEnabled(self.whitelist_enabled)

    def blacklist_enabled_changed(self, state):
        self.blacklist_enabled = state != 0
        self.config["blacklist_enabled"] = self.blacklist_enabled
        self.blacklist_line_edit.setEnabled(self.blacklist_enabled)

    def whitelist_changed(self):
        text = self.whitelist_line_edit.text().strip().replace(" ", "").lower()
        self.whitelist = text.split(",") if text else []
        self.config["whitelist"] = self.whitelist

    def blacklist_changed(self):
        text = self.blacklist_line_edit.text().strip().replace(" ", "").lower()
        self.blacklist = text.split(",") if text else []
        self.config["blacklist"] = self.blacklist
