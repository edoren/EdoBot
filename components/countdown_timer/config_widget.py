import os.path
from typing import Any, List, Mapping

from PySide6.QtCore import QCoreApplication, QFile, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (QComboBox, QGroupBox, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                               QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from model import EventType

from .form_widget import FormWidget
from .reward_timer import RewardTimer


class CountdownTimerWidget(QWidget):
    addButtonPressed = Signal(RewardTimer, int)
    subButtonPressed = Signal(RewardTimer, int)
    setButtonPressed = Signal(RewardTimer, int)

    def __init__(self, data_parent) -> None:
        super().__init__()

        self.data_parent = data_parent

        file = QFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "config.ui"))
        file.open(QFile.OpenModeFlag.ReadOnly)  # type: ignore
        my_widget = QUiLoader().load(file, self)
        file.close()

        # UI Elements

        self.timers_list: QListWidget = getattr(my_widget, "timers_list")
        self.add_timer_button: QPushButton = getattr(my_widget, "add_timer_button")
        self.remove_timer_button: QPushButton = getattr(my_widget, "remove_timer_button")
        self.timer_config_group_box: QGroupBox = getattr(my_widget, "timer_config_group_box")
        self.tab_widget: QTabWidget = getattr(my_widget, "tab_widget")

        self.format_input: QLineEdit = getattr(my_widget, "format_input")
        self.source_name_input: QLineEdit = getattr(my_widget, "source_name_input")
        self.display_selection: QComboBox = getattr(my_widget, "display_selection")
        self.start_message_input: QLineEdit = getattr(my_widget, "start_message_input")
        self.finish_message_input: QLineEdit = getattr(my_widget, "finish_message_input")
        self.add_time_button: QPushButton = getattr(my_widget, "add_time_button")
        self.sub_time_button: QPushButton = getattr(my_widget, "sub_time_button")
        self.add_sub_time_input: QSpinBox = getattr(my_widget, "add_sub_time_input")
        self.set_time_input: QSpinBox = getattr(my_widget, "set_time_input")
        self.set_time_button: QPushButton = getattr(my_widget, "set_time_button")
        self.clear_time_button: QPushButton = getattr(my_widget, "clear_time_button")

        self.active_events_list: QListWidget = getattr(my_widget, "active_events_list")
        self.available_events_list: QListWidget = getattr(my_widget, "available_events_list")
        self.add_event_button: QPushButton = getattr(my_widget, "add_event_button")

        self.event_config: QGroupBox = getattr(my_widget, "event_config")
        self.event_config_layout: QVBoxLayout = getattr(my_widget, "event_config_layout")
        self.event_duration_input: QSpinBox = getattr(my_widget, "event_duration_input")
        self.event_duration_format: QComboBox = getattr(my_widget, "event_duration_format")

        # Default Configs

        self.timer_config_group_box.setEnabled(False)
        self.remove_timer_button.setEnabled(False)

        self.display_selection.addItem(QCoreApplication.translate("CountdownTimerCompConfig", "Hours", None), "hours")
        self.display_selection.addItem(QCoreApplication.translate("CountdownTimerCompConfig", "Minutes", None),
                                       "minutes")
        self.display_selection.addItem(QCoreApplication.translate("CountdownTimerCompConfig", "Seconds", None),
                                       "seconds")
        self.display_selection.addItem(QCoreApplication.translate("CountdownTimerCompConfig", "Automatic", None),
                                       "automatic")
        self.display_selection.setCurrentIndex(self.display_selection.findData("minutes"))

        self.event_type_names = {
            "prime": QCoreApplication.translate("CountdownTimerCompConfig", "Prime", None),
            "1000": QCoreApplication.translate("CountdownTimerCompConfig", "Tier 1", None),
            "2000": QCoreApplication.translate("CountdownTimerCompConfig", "Tier 2", None),
            "3000": QCoreApplication.translate("CountdownTimerCompConfig", "Tier 3", None),
            "any": QCoreApplication.translate("CountdownTimerCompConfig", "Any", None),
        }

        self.available_events = {
            EventType.SUBSCRIPTION: {
                "name": QCoreApplication.translate("CountdownTimerCompConfig", "Subscription", None),
                "form": [{
                    "id": "is_gift",
                    "type": "check_box",
                    "default": False,
                    "title": QCoreApplication.translate("CountdownTimerCompConfig", "Is Gift?", None)
                }, {
                    "id": "type",
                    "type": "combo_box",
                    "title": QCoreApplication.translate("CountdownTimerCompConfig", "Subscription Type", None),
                    "default": "prime",
                    "choices": [{
                        "value": "prime",
                        "name": self.event_type_names["prime"],
                    }, {
                        "value": "1000",
                        "name": self.event_type_names["1000"],
                    }, {
                        "value": "2000",
                        "name": self.event_type_names["2000"],
                    }, {
                        "value": "3000",
                        "name": self.event_type_names["3000"],
                    }, {
                        "value": "any",
                        "name": self.event_type_names["any"],
                    }]
                }]
            },
            EventType.BITS: {
                "name": QCoreApplication.translate("CountdownTimerCompConfig", "Bits", None),
                "form": [{
                    "id": "is_exact",
                    "type": "check_box",
                    "default": False,
                    "title": QCoreApplication.translate("CountdownTimerCompConfig", "Is Exact?", None)
                }, {
                    "id": "num_bits",
                    "type": "number_box",
                    "default": 100,
                    "title": QCoreApplication.translate("CountdownTimerCompConfig", "Number of Bits", None)
                }]
            },
            EventType.REWARD_REDEEMED: {
                "name": QCoreApplication.translate("CountdownTimerCompConfig", "Channel Points", None),
                "form": [{
                    "id": "name",
                    "type": "text_box",
                    "default": "",
                    "title": QCoreApplication.translate("CountdownTimerCompConfig", "Reward Name", None)
                }]
            },
        }

        for key, data in self.available_events.items():
            item = QListWidgetItem(data.get("name", ""))  # type: ignore
            item.setData(Qt.UserRole, key)  # type: ignore
            self.available_events_list.addItem(item)
        self.available_events_list.setCurrentRow(0)

        self.event_config.setVisible(False)
        self.event_duration_format.addItem(QCoreApplication.translate("CountdownTimerCompConfig", "Hours", None),
                                           "hours")
        self.event_duration_format.addItem(QCoreApplication.translate("CountdownTimerCompConfig", "Minutes", None),
                                           "minutes")
        self.event_duration_format.addItem(QCoreApplication.translate("CountdownTimerCompConfig", "Seconds", None),
                                           "seconds")
        self.event_duration_format.setCurrentIndex(self.event_duration_format.findData("seconds"))

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

        self.add_time_button.clicked.connect(lambda _: self.addButtonPressed.emit(  # type: ignore
            self.__get_current_selected_timer(),
            self.add_sub_time_input.value() * 1000))
        self.sub_time_button.clicked.connect(lambda _: self.subButtonPressed.emit(  # type: ignore
            self.__get_current_selected_timer(), -self.add_sub_time_input.value() * 1000))
        self.set_time_button.clicked.connect(lambda _: self.setButtonPressed.emit(  # type: ignore
            self.__get_current_selected_timer(),
            self.set_time_input.value() * 1000))
        self.clear_time_button.clicked.connect(lambda _: self.setButtonPressed.emit(  # type: ignore
            self.__get_current_selected_timer(), 0))

        self.event_duration_format.activated.connect(  # type: ignore
            lambda index: self.update_active_event_data("duration_format", self.event_duration_format.itemData(index)))

        self.add_event_button.clicked.connect(lambda _: self.add_timer_event_clicked())  # type: ignore
        self.active_events_list.itemChanged.connect(self.active_events_item_changed)  # type: ignore
        self.active_events_list.currentItemChanged.connect(self.active_events_selection_changed)  # type: ignore
        self.active_events_list.customContextMenuRequested.connect(self.open_active_events_context_menu)  # type: ignore
        self.event_duration_input.editingFinished.connect(  # type: ignore
            lambda: self.update_active_event_data("duration", self.event_duration_input.value()))
        self.event_duration_format.activated.connect(  # type: ignore
            lambda index: self.update_active_event_data("duration_format", self.event_duration_format.itemData(index)))

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
        timer = self.data_parent.add_timer(QCoreApplication.translate("CountdownTimerCompConfig", "New Timer", None))
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

    def remove_selected_timer(self):
        selected_item: QListWidgetItem = self.timers_list.selectedItems()[0]
        timer: RewardTimer = selected_item.data(Qt.UserRole)  # type: ignore
        ret = QMessageBox.question(
            self, QCoreApplication.translate("CountdownTimerCompConfig", "Remove Timer?", None),
            QCoreApplication.translate("CountdownTimerCompConfig", "Do you want to remove the <b>{0}</b> timer?",
                                       None).format(timer.name), QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            self.data_parent.remove_timer(timer.id)
            self.tab_widget.setCurrentIndex(0)
            self.timers_list.takeItem(self.timers_list.row(selected_item))

    def update_timer_data(self, name: str, data: Any):
        timer = self.__get_current_selected_timer()
        setattr(timer, name, data)
        self.data_parent.save_timers()

    def timer_selection_changed(self, current, previous):
        if current is None:
            self.timer_config_group_box.setEnabled(False)
            self.remove_timer_button.setEnabled(False)
        else:
            self.timer_config_group_box.setEnabled(True)
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
                QMessageBox.critical(
                    self, QCoreApplication.translate("CountdownTimerCompConfig", "Error Creating Timer", None),
                    QCoreApplication.translate("CountdownTimerCompConfig", "The timer name should not be empty", None))
                self.timers_list.takeItem(self.timers_list.row(item))
                return
            timer.name = item.text()
            timer_has_changes = True

        if timer_has_changes:
            self.data_parent.save_timers()

    # Event slots

    def add_timer_event_clicked(self):
        selected_event = self.available_events_list.selectedItems()[0]
        timer: RewardTimer = self.__get_current_selected_timer()
        type_: EventType = selected_event.data(Qt.UserRole)
        new_event = self.data_parent.add_timer_event(type_, timer.id)
        if new_event:
            self.add_timer_event(new_event)
            self.active_events_list.setCurrentRow(self.active_events_list.model().rowCount() - 1)

    def add_timer_event(self, event: RewardTimer.Event):
        item = QListWidgetItem()
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)  # type: ignore
        item.setCheckState(Qt.Checked if event.enabled else Qt.Unchecked)  # type: ignore
        item.setText(self.__get_event_title(event))
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
        num_elements = self.event_config_layout.count()
        if num_elements > 2:
            layout_item = self.event_config_layout.itemAt(0)
            layout_item.widget().deleteLater()

        if current is None:
            self.event_config.setVisible(False)
        else:
            self.event_config.setVisible(True)
            event: RewardTimer.Event = current.data(Qt.UserRole)  # type: ignore
            self.event_duration_input.setValue(event.duration)
            self.event_duration_format.setCurrentIndex(self.event_duration_format.findData(event.duration_format))
            if event.type in self.available_events:
                data = self.available_events[event.type]
                form: List[Mapping[str, str]] = data["form"]  # type: ignore
                widget = FormWidget(None, form, event.data)
                widget.valueChanged.connect(  # type: ignore
                    lambda key, val: self.update_active_event_data(key, val, True))
                self.event_config_layout.insertWidget(0, widget)
                widget.set_values(event.data)

    def update_active_event_data(self, name: str, data: Any, is_custom=False):
        selected_item: QListWidgetItem = self.active_events_list.selectedItems()[0]
        event: RewardTimer.Event = selected_item.data(Qt.UserRole)  # type: ignore
        if is_custom:
            event.data[name] = data
        else:
            setattr(event, name, data)
        self.data_parent.save_timers()
        selected_item.setText(self.__get_event_title(event))

    def open_active_events_context_menu(self, position):
        if self.active_events_list.itemAt(position):
            menu = QMenu()
            delete_action = QAction(
                QCoreApplication.translate("CountdownTimerCompConfig", "Delete", None),  # type: ignore
                self.active_events_list)
            menu.addAction(delete_action)
            delete_action.triggered.connect(self.remove_timer_event_clicked)  # type: ignore
            menu.exec_(self.active_events_list.mapToGlobal(position))

    # Utils

    def __get_current_selected_timer(self) -> RewardTimer:
        selected_item = self.timers_list.selectedItems()[0]
        return selected_item.data(Qt.UserRole)

    def __get_event_title(self, event: RewardTimer.Event) -> str:
        type_name = QCoreApplication.translate("CountdownTimerCompConfig", "Unknown", None)
        if event.type is not None and event.type in self.available_events:
            type_name = self.available_events[event.type]["name"]
        event_title = f"{type_name}:"
        if event.type == EventType.REWARD_REDEEMED:
            event_title += " {} ".format(event.data["name"])
        elif event.type == EventType.SUBSCRIPTION:
            event_title += " {} ".format(self.event_type_names[event.data["type"]])
            if event.data["is_gift"]:
                event_title += "{} ".format(QCoreApplication.translate("CountdownTimerCompConfig", "Gift", None))
        elif event.type == EventType.BITS:
            event_title += " {} ".format(event.data["num_bits"])
            if event.data["is_exact"]:
                event_title += "{} ".format(QCoreApplication.translate("CountdownTimerCompConfig", "Exactly", None))
        event_title += f"- {event.duration} {event.duration_format}"
        return event_title
