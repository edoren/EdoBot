import logging
import os.path
import threading
import time
import uuid
from typing import Any, List, Mapping, MutableMapping, Optional, Set, Union

import obswebsocket.requests as obs_requests
from PySide2.QtCore import QCoreApplication, QFile, Qt
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import (QAction, QComboBox, QFormLayout, QGroupBox, QLineEdit, QListWidget, QListWidgetItem,
                               QMenu, QMessageBox, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

import twitch
from core import ChatComponent
from model import User, UserType

gLogger = logging.getLogger("edobot.components.counter")


class RewardTimer:
    class Event:
        def __init__(self, type: str, **kwargs: Any):
            self.id: str = kwargs.get("id", uuid.uuid4().hex)
            self.type: str = type
            self.enabled: bool = kwargs.get("enabled", True)
            self.duration: int = kwargs.get("duration", 30)
            self.description: str = kwargs.get("description", "")
            self.data: MutableMapping[str, Any] = kwargs.get("data", {})

        def serialize(self) -> Mapping[str, Any]:
            return {
                "id": self.id,
                "type": self.type,
                "enabled": self.enabled,
                "duration": self.duration,
                "description": self.description,
                "data": self.data
            }

    def __init__(self, name: str, **kwargs: Any):
        self.id: str = kwargs.get("id", uuid.uuid4().hex)
        self.name: str = name
        self.enabled: bool = kwargs.get("enabled", True)
        self.display: str = kwargs.get("display", "minutes")
        self.format: str = kwargs.get("format", "{name}: {time}")
        self.display: str = kwargs.get("display", "minutes")
        self.source: str = kwargs.get("source", "")
        self.start_msg: str = kwargs.get("start_msg", "")
        self.finish_msg: str = kwargs.get("finish_msg", "")
        self.events: List[RewardTimer.Event] = [RewardTimer.Event(**x) for x in kwargs.get("events", [])]

    def __hash__(self):
        return hash((self.id, self.name))

    def __eq__(self, other):
        return (self.id, self.name) == (other.id, other.name)

    def __ne__(self, other):
        return not (self == other)

    def has_event(self, type: str, **kwargs: Any) -> bool:
        return self.get_event(type, **kwargs) is not None

    def get_event(self, type: str, **kwargs: Any) -> Optional["RewardTimer.Event"]:
        for event in self.events:
            if event.type == type:
                if kwargs:
                    if not event.data:
                        return None
                    comp = True
                    for key in kwargs:
                        comp = comp and (key in event.data and kwargs[key] == event.data[key])
                    if comp:
                        return event
                else:
                    return event
        return None

    def serialize(self) -> Mapping[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "display": self.display,
            "format": self.format,
            "source": self.source,
            "start_msg": self.start_msg,
            "finish_msg": self.finish_msg,
            "events": [x.serialize() for x in self.events]
        }


class CountdownTimerWidget(QWidget):
    def __init__(self, data_parent: "CountdownTimerComponent") -> None:
        super().__init__()

        self.data_parent = data_parent

        file = QFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "countdown_timer.ui"))
        file.open(QFile.OpenModeFlag.ReadOnly)  # type: ignore
        my_widget = QUiLoader().load(file, self)
        file.close()

        # UI Elements

        self.timers_list: QListWidget = getattr(my_widget, "timers_list")
        self.add_timer_button: QPushButton = getattr(my_widget, "add_timer_button")
        self.remove_timer_button: QPushButton = getattr(my_widget, "remove_timer_button")
        self.timer_config: QGroupBox = getattr(my_widget, "timer_config")
        self.tab_widget: QTabWidget = getattr(my_widget, "tab_widget")

        self.format_input: QLineEdit = getattr(my_widget, "format_input")
        self.source_name_input: QLineEdit = getattr(my_widget, "source_name_input")
        self.display_selection: QComboBox = getattr(my_widget, "display_selection")
        self.start_message_input: QLineEdit = getattr(my_widget, "start_message_input")
        self.finish_message_input: QLineEdit = getattr(my_widget, "finish_message_input")

        self.active_events_list: QListWidget = getattr(my_widget, "active_events_list")
        self.available_events_list: QListWidget = getattr(my_widget, "available_events_list")
        self.add_event_button: QPushButton = getattr(my_widget, "add_event_button")

        self.event_config: QGroupBox = getattr(my_widget, "event_config")
        self.event_duration_input: QSpinBox = getattr(my_widget, "event_duration_input")
        self.event_duration_format: QComboBox = getattr(my_widget, "event_duration_format")
        self.event_data_form: QFormLayout = getattr(my_widget, "event_data_form")

        # Default Configs

        self.timer_config.setEnabled(False)
        self.remove_timer_button.setEnabled(False)

        self.display_selection.addItem("Hours", "hours")
        self.display_selection.addItem("Minutes", "minutes")
        self.display_selection.addItem("Seconds", "seconds")
        self.display_selection.setCurrentIndex(self.display_selection.findData("minutes"))

        self.available_events = {"reward": "Channel Points"}

        for key, name in self.available_events.items():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, key)  # type: ignore
            self.available_events_list.addItem(item)
        self.available_events_list.setCurrentRow(0)

        self.event_config.setVisible(False)
        self.event_duration_format.setVisible(False)
        self.event_data_form_initial_num = self.event_data_form.rowCount()

        # Slot connections

        self.timers_list.itemChanged.connect(self.timer_item_changed)  # type: ignore
        self.timers_list.currentItemChanged.connect(self.timer_selection_changed)  # type: ignore
        self.add_timer_button.clicked.connect(lambda _: self.add_timer_clicked())  # type: ignore
        self.remove_timer_button.clicked.connect(lambda _: self.remove_selected_timer())  # type: ignore

        self.format_input.editingFinished.connect(  # type: ignore
            lambda: self.update_timer_data("format",
                                           self.format_input.text().strip()))
        self.source_name_input.editingFinished.connect(  # type: ignore
            lambda: self.update_timer_data("source",
                                           self.source_name_input.text().strip()))
        self.display_selection.activated.connect(  # type: ignore
            lambda index: self.update_timer_data("display", self.display_selection.itemData(index)))
        self.start_message_input.editingFinished.connect(  # type: ignore
            lambda: self.update_timer_data("start_msg",
                                           self.start_message_input.text().strip()))
        self.finish_message_input.editingFinished.connect(  # type: ignore
            lambda: self.update_timer_data("finish_msg",
                                           self.finish_message_input.text().strip()))

        self.add_event_button.clicked.connect(lambda _: self.add_timer_event_clicked())  # type: ignore
        self.active_events_list.itemChanged.connect(self.active_events_item_changed)  # type: ignore
        self.active_events_list.currentItemChanged.connect(self.active_events_selection_changed)  # type: ignore
        self.active_events_list.customContextMenuRequested.connect(self.open_active_events_context_menu)  # type: ignore
        self.event_duration_input.editingFinished.connect(  # type: ignore
            self.event_duration_changed)

        layout = QVBoxLayout()
        layout.addWidget(my_widget)
        self.setLayout(layout)
        self.setMinimumWidth(my_widget.width())
        self.setMinimumHeight(my_widget.height())

        for timer in self.data_parent.get_timers():
            self.add_timer(timer)
        if self.timers_list.count():
            self.timers_list.setCurrentRow(0)

    # Timer slots

    def add_timer_clicked(self):
        timer = self.data_parent.add_timer("New Timer")
        item = self.add_timer(timer)
        self.tab_widget.setCurrentIndex(0)
        self.timers_list.editItem(item)
        self.timers_list.setCurrentItem(item)

    def add_timer(self, timer: RewardTimer) -> QListWidgetItem:
        item = QListWidgetItem()
        item.setText(timer.name)
        item.setFlags(item.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)  # type: ignore
        item.setCheckState(Qt.CheckState.Checked if timer.enabled else Qt.CheckState.Unchecked)
        item.setData(Qt.UserRole, timer)  # type: ignore
        self.timers_list.addItem(item)
        return item

    def remove_selected_timer(self, timer: Optional[RewardTimer] = None):
        selected_item: QListWidgetItem = self.timers_list.selectedItems()[0]
        self.data_parent.remove_timer(selected_item.data(Qt.UserRole).id)  # type: ignore
        self.tab_widget.setCurrentIndex(0)
        self.timers_list.takeItem(self.timers_list.row(selected_item))

    def update_timer_data(self, name: str, data: Any):
        selected_item = self.timers_list.selectedItems()[0]
        timer = selected_item.data(Qt.UserRole)
        setattr(timer, name, data)
        self.data_parent.save_timers()

    def timer_selection_changed(self, current, previous):
        if current is None:
            self.timer_config.setEnabled(False)
            self.remove_timer_button.setEnabled(False)
        else:
            self.timer_config.setEnabled(True)
            self.remove_timer_button.setEnabled(True)
            timer: RewardTimer = current.data(Qt.UserRole)  # type: ignore
            self.format_input.setText(timer.format)
            self.format_input.setText(timer.format)
            self.source_name_input.setText(timer.source)
            self.start_message_input.setText(timer.start_msg)
            self.finish_message_input.setText(timer.finish_msg)
            self.display_selection.setCurrentIndex(self.display_selection.findData(timer.display))
            self.active_events_list.clear()
            for event in timer.events:
                self.add_timer_event(event)
            self.event_config.setVisible(False)
            self.active_events_list.setCurrentRow(0)

    def timer_item_changed(self, item: QListWidgetItem):
        timer_has_changes = False
        timer: RewardTimer = item.data(Qt.UserRole)  # type: ignore

        enabled = (item.checkState() == Qt.CheckState.Checked)
        if timer.enabled != enabled:
            timer.enabled = enabled
            timer_has_changes = True

        name = item.text().replace("\n", " ").replace("\t", " ").strip()
        if timer.name != name:
            if name != item.text():
                item.setText(name)
                return
            if not item.text():
                QMessageBox.critical(self, "Error creating item", "New timer should not be empty")
                self.timers_list.takeItem(self.timers_list.row(item))
                return
            timer.name = item.text()
            timer_has_changes = True

        if timer_has_changes:
            self.data_parent.save_timers()

    # Event slots

    def add_timer_event_clicked(self):
        selected_timer = self.timers_list.selectedItems()[0]
        selected_event = self.available_events_list.selectedItems()[0]
        timer: RewardTimer = selected_timer.data(Qt.UserRole)
        type_: str = selected_event.data(Qt.UserRole)
        new_event = self.data_parent.add_timer_event(type_, timer.id)
        if new_event:
            self.add_timer_event(new_event)
            self.active_events_list.setCurrentRow(self.active_events_list.model().rowCount() - 1)

    def add_timer_event(self, event: RewardTimer.Event):
        item = QListWidgetItem()
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)  # type: ignore
        item.setCheckState(Qt.Checked if event.enabled else Qt.Unchecked)  # type: ignore
        type_name = self.available_events.get(event.type, "Unknown")
        if event.description:
            event_name = f"{type_name}: {event.description} - {event.duration} seconds"
        else:
            event_name = f"{type_name} - {event.duration} seconds"
        item.setText(event_name)
        item.setData(Qt.UserRole, event)  # type: ignore
        self.active_events_list.addItem(item)

    def remove_timer_event_clicked(self):
        selected_timer = self.timers_list.selectedItems()[0]
        selected_event = self.active_events_list.selectedItems()[0]
        timer: RewardTimer = selected_timer.data(Qt.UserRole)
        event: RewardTimer.Event = selected_event.data(Qt.UserRole)
        self.data_parent.remove_timer_event(timer.id, event.id)  # type: ignore
        self.active_events_list.takeItem(self.active_events_list.row(selected_event))

    def active_events_item_changed(self, item):
        event: RewardTimer.Event = item.data(Qt.UserRole)  # type: ignore
        enabled = (item.checkState() == Qt.CheckState.Checked)
        if event.enabled != enabled:
            event.enabled = enabled
            self.data_parent.save_timers()

    def active_events_selection_changed(self, current, previous):
        for row in range(0, self.event_data_form.rowCount() - self.event_data_form_initial_num):
            self.event_data_form.removeRow(row)

        if current is None:
            self.event_config.setVisible(False)
        else:
            self.event_config.setVisible(True)
            event: RewardTimer.Event = current.data(Qt.UserRole)  # type: ignore
            self.event_duration_input.setValue(event.duration)

            if event.type == "reward":
                name_input = QLineEdit(event.data.get("name", ""))
                self.event_data_form.insertRow(0, "Reward Name", name_input)
                name_input.editingFinished.connect(  # type: ignore
                    lambda: self.update_active_event_data("name",
                                                          name_input.text().strip(), True))
                name_input.textChanged.connect(  # type: ignore
                    lambda text: self.update_active_event_data("description", text.strip()))

    def update_active_event_data(self, name: str, data: Any, is_custom=False):
        selected_item: QListWidgetItem = self.active_events_list.selectedItems()[0]
        event: RewardTimer.Event = selected_item.data(Qt.UserRole)  # type: ignore
        if is_custom:
            event.data[name] = data
        else:
            setattr(event, name, data)
            self.data_parent.save_timers()
            event_name = self.available_events[event.type]
            if event.description:
                selected_item.setText(f"{event_name}: {event.description} - {event.duration} seconds")
            else:
                selected_item.setText(f"{event_name} - {event.duration} seconds")

    def event_duration_changed(self):
        self.update_active_event_data("duration", self.event_duration_input.value())

    def open_active_events_context_menu(self, position):
        if self.active_events_list.itemAt(position):
            menu = QMenu()
            delete_action = QAction(
                QCoreApplication.translate("CountdownTimer", "Delete", None),  # type: ignore
                self.active_events_list)
            menu.addAction(delete_action)
            delete_action.triggered.connect(self.remove_timer_event_clicked)  # type: ignore
            menu.exec_(self.active_events_list.mapToGlobal(position))


class CountdownTimerComponent(ChatComponent):  # TODO: Change to chat store
    @staticmethod
    def get_id() -> str:
        return "countdown_timer"

    @staticmethod
    def get_name() -> str:
        return "Countdown Timer"

    @staticmethod
    def get_description() -> str:
        return "Add a countdown that interacts with Channel Points, Subs or Bits"

    def __init__(self) -> None:
        super().__init__()
        self.counter_thread_lock = threading.Lock()  # TODO: add timer and event locks
        self.active_sources: MutableMapping[str, MutableMapping[RewardTimer, int]] = {}
        self.counter_thread: Optional[threading.Thread] = None

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return None  # To get all the messages without command filtering

    def start(self) -> None:
        self.__timers: List[RewardTimer] = [RewardTimer(**x) for x in self.config["timers"].setdefault([])]

        def counter_task():
            sources_to_hide: List[str] = []
            timers_to_delete: List[RewardTimer] = []
            while self.running:
                if not self.active_sources:
                    time.sleep(1)
                    continue
                current_time = round(time.time() * 1000)
                with self.counter_thread_lock:
                    for source_name, timers in self.active_sources.items():
                        source_text = ""
                        separator = "\n"
                        for timer, finish_time in timers.items():
                            tmleft = finish_time - current_time
                            tmlist = []
                            if timer.display == "hours":
                                tmlist.append("{:02d}".format(int((tmleft / 3600000))) if tmleft >= 0 else "00")
                            if timer.display == "hours" or timer.display == "minutes":
                                tmlist.append("{:02d}".format(int((tmleft/60000) % 60)) if tmleft >= 0 else "00")
                            if timer.display == "hours" or timer.display == "minutes" or timer.display == "seconds":
                                tmlist.append("{:02d}".format(int((tmleft/1000) % 60)) if tmleft >= 0 else "00")
                            if tmleft < 0:
                                if timer.finish_msg:
                                    self.chat.send_message(timer.finish_msg.replace("{name}", timer.name))
                                timers_to_delete.append(timer)
                            time_str = ":".join(tmlist)
                            source_text += timer.format.replace("{name}", timer.name).replace("{time}", time_str)
                            source_text += separator
                        source_text = source_text.strip(separator)
                        self.obs_client.call(obs_requests.SetTextGDIPlusProperties(source_name, text=source_text))
                        if timers_to_delete:
                            for timer in timers_to_delete:
                                # if timer in timers:
                                del timers[timer]
                            timers_to_delete.clear()
                        if not timers:
                            sources_to_hide.append(source_name)
                if sources_to_hide:
                    for source_name in sources_to_hide:
                        with self.counter_thread_lock:
                            del self.active_sources[source_name]
                        self.obs_client.call(obs_requests.SetTextGDIPlusProperties(source_name, text=""))
                    sources_to_hide.clear()
                time.sleep(0.1)

        self.running = True
        self.counter_thread = threading.Thread(target=counter_task, name="CountdownTimerThread")
        self.counter_thread.start()

        super().start()

    def stop(self) -> None:
        self.running = False
        if self.counter_thread is not None and self.counter_thread.is_alive():
            self.counter_thread.join()
        self.save_timers()
        super().stop()

    def process_message(self, message: str, user: User, user_types: Set[UserType],
                        metadata: Optional[Any] = None) -> None:
        pass

    def start_counter(self, timer: RewardTimer, event: RewardTimer.Event):
        with self.counter_thread_lock:
            source_name = timer.source
            duration = event.duration
            if source_name in self.active_sources and timer in self.active_sources[source_name]:
                self.active_sources[source_name][timer] += (duration * 1000)
            else:
                source_timers = self.active_sources.setdefault(source_name, {})
                source_timers[timer] = round((time.time() + duration) * 1000)
                if timer.start_msg:
                    self.chat.send_message(timer.start_msg.replace("{name}", timer.name))

    def process_event(self, event_name: str, metadata: Any) -> None:
        if not self.is_obs_connected():
            return
        if event_name == "REWARD_REDEEMED":
            event_data: twitch.ChannelPointsEventMessage = metadata
            reward_name = event_data.redemption.reward.title
            for timer in self.__timers:
                if timer.enabled:
                    event = timer.get_event("reward", name=reward_name)
                    if event is not None and event.enabled:
                        self.start_counter(timer, event)

    def get_config_something(self) -> Optional[QWidget]:
        return CountdownTimerWidget(self)

    def get_timers(self) -> List[RewardTimer]:
        return self.__timers

    def add_timer(self, name: str) -> RewardTimer:
        timer = RewardTimer(name)
        self.__timers.append(timer)
        self.save_timers()
        return timer

    def remove_timer(self, timer_id: str):
        index = None
        for i in range(len(self.__timers)):
            if self.__timers[i].id == timer_id:
                index = i
                break
        if index is not None:
            del self.__timers[index]
            self.save_timers()

    def add_timer_event(self, type_: str, timer_id: str) -> Optional[RewardTimer.Event]:
        for timer in self.__timers:
            if timer.id == timer_id:
                event_data = None
                if type_ == "reward":
                    event_data = {"name": ""}
                event = RewardTimer.Event(type_, data=event_data)
                timer.events.append(event)
                self.save_timers()
                return event

    def remove_timer_event(self, timer_id: str, event_id: str):
        for timer in self.__timers:
            if timer.id == timer_id:
                index = None
                for i in range(len(timer.events)):
                    if timer.events[i].id == event_id:
                        index = i
                        break
                if index is not None:
                    del timer.events[index]
                    self.save_timers()
                    break

    def save_timers(self):
        self.config["timers"] = [x.serialize() for x in self.__timers]
