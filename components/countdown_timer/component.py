import logging
import threading
import time
from typing import Any, List, MutableMapping, Optional, Set, Tuple, Union

import qtawesome as qta
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QWidget

from edobot.core import ChatComponent
from edobot.model import EventType, User, UserType
from edobot.services import twitch

from .config_widget import CountdownTimerWidget
from .reward_timer import RewardTimer

gLogger = logging.getLogger("edobot.components.counter")


class CountdownTimerComponent(ChatComponent):
    @staticmethod
    def get_id() -> str:
        return "countdown_timer"

    @staticmethod
    def get_metadata() -> ChatComponent.Metadata:
        return ChatComponent.Metadata(
            name=QCoreApplication.translate("CountdownTimerCompConfig", "Countdown Timer", None),
            description=QCoreApplication.translate(
                "CountdownTimerCompConfig", "Add a countdown that interacts with Channel Points, Subs or Bits", None
            ),
            icon=qta.icon("fa5.clock"),
        )

    def __init__(self) -> None:
        super().__init__()
        self.timer_thread_lock = threading.Lock()  # TODO: add timer and event locks
        self.active_sources_thread_lock = threading.Lock()  # TODO: add timer and event locks
        self.active_sources: MutableMapping[str, MutableMapping[str, Tuple[RewardTimer, int]]] = {}
        self.counter_thread: Optional[threading.Thread] = None
        self.widget: Optional[CountdownTimerWidget] = None

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return None  # To get all the messages without command filtering

    def start(self) -> None:
        self.__timers: List[RewardTimer] = [RewardTimer(**x) for x in self.config["timers"].setdefault([])]

        def counter_task():
            sources_to_hide: List[str] = []
            timers_to_delete: List[str] = []
            while self.running:
                if not self.active_sources:
                    time.sleep(1)
                    continue
                current_time = round(time.time() * 1000)
                with self.active_sources_thread_lock:
                    for source_name, timers in self.active_sources.items():
                        source_text = ""
                        separator = "\n"
                        for timer_id, val in timers.items():
                            timer, finish_time = val
                            tmleft = finish_time - current_time
                            if tmleft < 0:
                                if timer.finish_msg:
                                    self.chat.send_message(timer.finish_msg.replace("{name}", timer.name))
                                timers_to_delete.append(timer_id)
                                continue
                            time_str = self.format_time(tmleft, timer.display)
                            if self.widget:
                                self.widget.current_time_label.setText(
                                    self.format_time(tmleft, "hours") if timer.display != "hours" else time_str
                                )
                            source_text += timer.format.replace("{name}", timer.name).replace("{time}", time_str)
                            source_text += separator
                        source_text = source_text.strip(separator)
                        self.obs.set_text_gdi_plus_properties(source_name, text=source_text)
                        if timers_to_delete:
                            for timer in timers_to_delete:
                                del timers[timer]
                            timers_to_delete.clear()
                        if not timers:
                            sources_to_hide.append(source_name)
                if sources_to_hide:
                    for source_name in sources_to_hide:
                        with self.active_sources_thread_lock:
                            del self.active_sources[source_name]
                        self.obs.set_text_gdi_plus_properties(source_name, text="")
                        if self.widget:
                            self.widget.current_time_label.setText("00:00:00")
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

    def process_message(
        self, message: str, user: User, user_types: Set[UserType], metadata: Optional[Any] = None
    ) -> None:
        pass

    def process_event(self, event_type, metadata: Optional[Any] = None) -> None:
        if event_type not in (EventType.SUBSCRIPTION, EventType.BITS, EventType.REWARD_REDEEMED, EventType.RAID):
            return

        with self.timer_thread_lock:
            for timer in self.__timers:
                if timer.enabled and metadata is not None:
                    if event_type == EventType.REWARD_REDEEMED:
                        points_event: twitch.events.ChannelPointsEvent = metadata
                        reward_name = points_event.redemption.reward.title
                        events = timer.get_events(event_type, name=reward_name)
                        for event in events:
                            if event.enabled:
                                self.add_time_to_timer(timer, event.get_duration_ms())
                    elif event_type == EventType.SUBSCRIPTION:
                        sub_event: twitch.events.SubscriptionEvent = metadata
                        events = timer.get_events(
                            event_type, is_gift=sub_event.is_gift, type=sub_event.sub_plan.lower()
                        )
                        for event in events:
                            if event.enabled:
                                self.add_time_to_timer(timer, event.get_duration_ms())
                    elif event_type == EventType.BITS:
                        bits_event: twitch.events.BitsEvent = metadata
                        events = timer.get_events(event_type)
                        nbits = bits_event.total_bits_used
                        for event in events:
                            if event.enabled:
                                if event.data["is_exact"]:
                                    if event.data["num_bits"] == nbits:
                                        self.add_time_to_timer(timer, event.get_duration_ms())
                                else:
                                    ratio = nbits / event.data["num_bits"]
                                    self.add_time_to_timer(timer, int(event.get_duration_ms() * ratio))
                    elif event_type == EventType.RAID:
                        raid_event: twitch.events.RaidEvent = metadata
                        events = timer.get_events(event_type)
                        viewer_count = raid_event.viewer_count
                        for event in events:
                            if event.enabled:
                                if viewer_count >= event.data["min_people"]:
                                    ratio = viewer_count / event.data["num_people"]
                                    self.add_time_to_timer(timer, int(event.get_duration_ms() * ratio))

    def get_config_ui(self) -> QWidget | dict[str, Any] | None:
        self.widget = CountdownTimerWidget(self)
        self.widget.addButtonPressed.connect(self.add_time_to_timer)  # type: ignore
        self.widget.subButtonPressed.connect(self.add_time_to_timer)  # type: ignore
        self.widget.setButtonPressed.connect(self.set_timer_time)  # type: ignore

        def clean_widget(_):
            with self.active_sources_thread_lock:
                self.widget = None

        self.widget.destroyed.connect(clean_widget)  # type: ignore
        return self.widget

    def add_time_to_timer(self, timer: RewardTimer, duration_ms: int):
        with self.active_sources_thread_lock:
            source_name = timer.source
            if source_name in self.active_sources and timer.id in self.active_sources[source_name]:
                timer, finish_time = self.active_sources[source_name][timer.id]
                self.active_sources[source_name][timer.id] = (timer, finish_time + duration_ms)
            elif duration_ms > 0:
                current_time = round(time.time() * 1000)
                finish_time = current_time + duration_ms
                source_timers = self.active_sources.setdefault(source_name, {})
                source_timers[timer.id] = (timer, finish_time)
                if timer.start_msg:
                    self.chat.send_message(timer.start_msg.replace("{name}", timer.name))

    def set_timer_time(self, timer: RewardTimer, duration_ms: int):
        if duration_ms < 0:
            duration_ms = 0
        with self.active_sources_thread_lock:
            current_time = round(time.time() * 1000)
            source_timers = self.active_sources.setdefault(timer.source, {})
            if not source_timers and timer.start_msg and duration_ms != 0:
                self.chat.send_message(timer.start_msg.replace("{name}", timer.name))
            source_timers[timer.id] = (timer, current_time + duration_ms)

    def format_time(self, time_ms: int, display_format: str) -> str:
        if display_format == "hours":
            return "{:02d}:{:02d}:{:02d}".format(
                int((time_ms / 3600000)), int((time_ms / 60000) % 60), int((time_ms / 1000) % 60)
            )
        elif display_format == "minutes":
            return "{:02d}:{:02d}".format(int((time_ms / 60000)), int((time_ms / 1000) % 60))
        elif display_format == "seconds":
            return "{:02d}".format(int((time_ms / 1000)))
        else:  # automatic
            if time_ms > 3600000:
                return self.format_time(time_ms, "hours")
            elif time_ms > 60000:
                return self.format_time(time_ms, "minutes")
            else:
                return self.format_time(time_ms, "seconds")

    def get_timers(self) -> List[RewardTimer]:
        with self.timer_thread_lock:
            return self.__timers.copy()

    def add_timer(self, name: str) -> RewardTimer:
        timer = RewardTimer(name)
        with self.timer_thread_lock:
            self.__timers.append(timer)
            self.save_timers_no_lock()
        return timer

    def remove_timer(self, timer_id: str):
        index = None
        with self.timer_thread_lock:
            for i in range(len(self.__timers)):
                if self.__timers[i].id == timer_id:
                    index = i
                    break
            if index is not None:
                timer = self.__timers[index]
                self.set_timer_time(timer, 0)
                del self.__timers[index]
                self.save_timers_no_lock()

    def add_timer_event(self, type_: EventType, timer_id: str) -> Optional[RewardTimer.Event]:
        with self.timer_thread_lock:
            for timer in self.__timers:
                if timer.id == timer_id:
                    event = RewardTimer.Event(type=type_)
                    timer.events.append(event)
                    self.save_timers_no_lock()
                    return event

    def remove_timer_event(self, timer_id: str, event_id: str):
        with self.timer_thread_lock:
            for timer in self.__timers:
                if timer.id == timer_id:
                    index = None
                    for i in range(len(timer.events)):
                        if timer.events[i].id == event_id:
                            index = i
                            break
                    if index is not None:
                        del timer.events[index]
                        self.save_timers_no_lock()
                        break

    def save_timers(self):
        with self.timer_thread_lock:
            self.save_timers_no_lock()

    def save_timers_no_lock(self):
        self.config["timers"] = [x.serialize() for x in self.__timers]
