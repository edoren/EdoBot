import logging
import os.path
from typing import Any, List, Mapping, Optional, Set, Union

import obswebsocket.requests as obs_requests
from PySide2.QtCore import QCoreApplication, QFile
from PySide2.QtGui import QShowEvent
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import (QAction, QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMenu, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from core import ChatComponent
from model import User, UserType

gLogger = logging.getLogger("edobot.components.scene_changer")

__all__ = ["SceneChangerComponent"]


class SceneChangerComponentConfigWidget(QWidget):
    def __init__(self, data_parent: "SceneChangerComponent") -> None:
        super().__init__()

        self.data_parent = data_parent

        file = QFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scene_changer.ui"))
        file.open(QFile.OpenModeFlag.ReadOnly)  # type: ignore
        my_widget = QUiLoader().load(file, self)
        file.close()

        self.command_line_edit: QLineEdit = getattr(my_widget, "command_line_edit")
        self.from_combo_box: QComboBox = getattr(my_widget, "from_combo_box")
        self.to_combo_box: QComboBox = getattr(my_widget, "to_combo_box")
        self.scene_changes_widget: QListWidget = getattr(my_widget, "scene_changes_widget")
        self.add_button: QPushButton = getattr(my_widget, "add_button")

        self.mod_check_box: QCheckBox = getattr(my_widget, "mod_check_box")
        self.vip_check_box: QCheckBox = getattr(my_widget, "vip_check_box")
        self.sub_check_box: QCheckBox = getattr(my_widget, "sub_check_box")
        self.chatter_check_box: QCheckBox = getattr(my_widget, "chatter_check_box")

        # Connect signals
        self.add_button.clicked.connect(self.on_add_clicked)  # type: ignore
        self.scene_changes_widget.customContextMenuRequested.connect(self.open_context_menu)  # type: ignore
        self.command_line_edit.editingFinished.connect(self.command_changed)  # type: ignore
        self.mod_check_box.clicked.connect(self.who_can_use_changed)  # type: ignore
        self.vip_check_box.clicked.connect(self.who_can_use_changed)  # type: ignore
        self.sub_check_box.clicked.connect(self.who_can_use_changed)  # type: ignore
        self.chatter_check_box.clicked.connect(self.who_can_use_changed)  # type: ignore

        layout = QVBoxLayout()
        layout.addWidget(my_widget)
        self.setLayout(layout)
        self.setMinimumWidth(self.width())

        self.command_line_edit.setText(self.data_parent.command)
        self.mod_check_box.setChecked(UserType.MODERATOR in self.data_parent.who_can)
        self.vip_check_box.setChecked(UserType.VIP in self.data_parent.who_can)
        self.sub_check_box.setChecked(UserType.SUBSCRIPTOR in self.data_parent.who_can)
        self.chatter_check_box.setChecked(UserType.CHATTER in self.data_parent.who_can)
        self.update_list_items()

    def update_list_items(self):
        transitions = self.data_parent.get_transitions()
        self.scene_changes_widget.clear()
        for from_transition, to_list in transitions.items():
            for to_transition in to_list:
                widget = QWidget()
                layout = QHBoxLayout()
                label = QLabel(from_transition)
                label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                layout.addWidget(label)
                label = QLabel("->")
                label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
                layout.addWidget(label)
                label = QLabel(to_transition)
                label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                layout.addWidget(label)
                layout.setContentsMargins(0, 2, 0, 2)
                widget.setLayout(layout)
                item = QListWidgetItem(f"{from_transition}||{to_transition}")
                item.setSizeHint(widget.sizeHint())
                self.scene_changes_widget.addItem(item)
                self.scene_changes_widget.setItemWidget(item, widget)

    def on_add_clicked(self):
        self.data_parent.add_transition(self.from_combo_box.currentText(), self.to_combo_box.currentText())
        self.update_list_items()

    def open_context_menu(self, position):
        if self.scene_changes_widget.itemAt(position):
            menu = QMenu()
            delete_action = QAction(
                QCoreApplication.translate("SceneChangerConfig", "Delete", None),  # type: ignore
                self.scene_changes_widget)
            menu.addAction(delete_action)
            delete_action.triggered.connect(self.delete_item_selection)  # type: ignore
            menu.exec_(self.scene_changes_widget.mapToGlobal(position))

    def delete_item_selection(self):
        for item in self.scene_changes_widget.selectedItems():
            pair = item.text().split("||")
            self.data_parent.remove_transition(pair[0], pair[1])
        self.update_list_items()

    def command_changed(self):
        self.data_parent.set_command(self.command_line_edit.text())

    def who_can_use_changed(self):
        self.data_parent.update_who_can(self.mod_check_box.isChecked(), self.vip_check_box.isChecked(),
                                        self.sub_check_box.isChecked(), self.chatter_check_box.isChecked())

    def showEvent(self, event: QShowEvent) -> None:
        scene_list = self.data_parent.get_obs_scenes()
        self.from_combo_box.clear()
        self.to_combo_box.clear()
        self.from_combo_box.addItems(scene_list)
        self.to_combo_box.addItems(scene_list)
        event.accept()


class SceneChangerComponent(ChatComponent):
    @staticmethod
    def get_id() -> str:
        return "scene_changer"

    @staticmethod
    def get_name() -> str:
        return "Scene Changer"

    @staticmethod
    def get_description() -> str:
        return "Allows chat to change the OBS scenes"

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return self.command

    def start(self) -> None:
        # Create the default configs if they dont exist
        self.command = ~self.config["command"]
        if self.command is None or not isinstance(self.command, str):
            self.command = "scene"
            self.config["command"] = self.command

        who_can = ~self.config["who_can"]
        if who_can is not None or isinstance(who_can, dict):
            self.update_who_can(who_can["mod"], who_can["vip"], who_can["sub"], who_can["chatter"])
        else:
            self.update_who_can(True, False, False, False)

        self.transitions = ~self.config["transitions"]
        if self.command is None or not isinstance(self.transitions, dict):
            self.transitions = {}
            self.config["transitions"] = {}

        super().start()

    def stop(self) -> None:
        super().stop()

    def process_message(self, message: str, user: User, user_types: Set[UserType],
                        metadata: Optional[Any] = None) -> None:
        if not self.is_obs_connected():
            return

        if len(self.who_can.intersection(user_types)) != 0:
            scenes_request: obs_requests.GetSceneList = self.obs_client.call(obs_requests.GetSceneList())
            scenes: List[Mapping[str, Any]] = scenes_request.getScenes()

            # Find a suitable scene target name
            target_scene = None
            for scene in scenes:
                if scene["name"].lower() == message.lower():
                    target_scene = scene["name"]

            if target_scene is not None:
                current_scene = scenes_request.getCurrentScene()
                if current_scene in self.transitions:
                    if target_scene in self.transitions[current_scene]:
                        gLogger.info(f"[{user.display_name}] Transitioning: {current_scene} -> {target_scene}")
                        self.obs_client.call(obs_requests.SetCurrentScene(target_scene))

    def process_event(self, event_name: str, metadata: Any) -> None:
        pass

    def get_config_something(self) -> Optional[QWidget]:
        return SceneChangerComponentConfigWidget(self)

    def add_transition(self, from_scene: str, to_scene: str):
        if from_scene not in self.transitions:
            self.transitions[from_scene] = []
        if to_scene not in self.transitions[from_scene]:
            self.transitions[from_scene].append(to_scene)
            self.config["transitions"] = self.transitions

    def remove_transition(self, from_scene: str, to_scene: str):
        if from_scene not in self.transitions or to_scene not in self.transitions[from_scene]:
            return
        self.transitions[from_scene].remove(to_scene)
        self.config["transitions"] = self.transitions

    def get_transitions(self) -> Mapping[str, List[str]]:
        return self.transitions

    def set_command(self, command: str):
        self.command = command
        self.config["command"] = self.command

    def update_who_can(self, mod: bool, vip: bool, sub: bool, chatter: bool):
        self.who_can = set()
        if mod:
            self.who_can.add(UserType.MODERATOR)
        if vip:
            self.who_can.add(UserType.VIP)
        if sub:
            self.who_can.add(UserType.SUBSCRIPTOR)
        if chatter:
            self.who_can.add(UserType.CHATTER)
        self.config["who_can"] = {"mod": mod, "vip": vip, "sub": sub, "chatter": chatter}

    def get_obs_scenes(self) -> List[str]:
        if not self.is_obs_connected():
            return []
        scenes_request: obs_requests.GetSceneList = self.obs_client.call(obs_requests.GetSceneList())
        return [scene["name"] for scene in scenes_request.getScenes()]
