import logging
import time
from typing import Any, Callable, List, Mapping, Optional

from model import EventType
from network import WebSocket
from twitch.chat_events import RaidEventMessage
from twitch.irc_tags import PrivateMsgTags

__all__ = ["Chat", "PrivateMsgTags"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class Chat(WebSocket):
    MessageCallable = Callable[[str, PrivateMsgTags, str], None]
    EventCallable = Callable[[EventType, Any], None]

    def __init__(self, nickname: str, password: str, channel_name: str):
        super().__init__("wss://irc-ws.chat.twitch.tv", timeout=1)

        self.nickname = nickname.lower()
        self.password = password
        self.channel_name = channel_name.lower()
        self.last_ping_time: Optional[float] = None
        self.has_started = False
        self.subscribers: List[Chat.MessageCallable] = []
        self.subscribers_events: List[Chat.EventCallable] = []

    def start(self) -> None:
        self.connect()
        super().start()

    def connect(self) -> None:
        if not self.connected:
            gLogger.info("Starting Chat connection...")
            self.has_started = False
            super().connect()
            if self.connected:
                # Authenticate
                self.send(f"PASS oauth:{self.password}")
                self.send(f"NICK {self.nickname}")
                # Require tags capability
                self.send("CAP REQ :twitch.tv/tags")
                # Require commands capability
                self.send("CAP REQ :twitch.tv/commands")
                # Join the desired channel
                self.send(f"JOIN #{self.channel_name}")

    def disconnect(self) -> None:
        super().disconnect()
        self.subscribers.clear()

    def subscribe(self, subscriber: MessageCallable):
        self.subscribers.append(subscriber)

    def subscribe_events(self, subscriber: EventCallable):
        self.subscribers_events.append(subscriber)

    def send_message(self, message: str) -> None:
        while self.running:
            try:
                self.send(f"PRIVMSG #{self.channel_name} :{message}")
                break
            except Exception as e:
                gLogger.error(f"Error sending message: {e}")
                time.sleep(0.1)

    def handle_message(self, message: str):
        lines = message.strip("\r\n").split("\r\n")

        def process_tags(tags_str: str) -> Mapping[str, str]:
            tags_dict = {}
            for key_value in tags_raw.lstrip("@").split(";"):
                key, value = key_value.split("=", 1)
                if key not in ["subscriber", "turbo", "user-type"]:  # Ignore deprecated tags
                    tags_dict[key.replace("-", "_")] = value
            return tags_dict

        for line in lines:
            if line.find("PRIVMSG") > 0:
                gLogger.debug(line)

                raw_message_list = line.rsplit("PRIVMSG", 1)
                tags_raw, sender_raw = raw_message_list[0].strip(" ").rsplit(" ", 1)
                tags = PrivateMsgTags(**process_tags(tags_raw))
                sender = sender_raw.split("!")[0].lstrip(":")

                if not tags.display_name:  # display_name might be empty
                    tags.display_name = sender

                _, text = raw_message_list[1].split(":", 1)  # channel, text

                sender = sender.strip("# ")
                text = text.strip(" ")
                for sub in self.subscribers:
                    sub(sender, tags, text)
            elif line.find("USERNOTICE") > 0:
                raw_message_list = line.rsplit("USERNOTICE", 1)
                tags_raw, sender_raw = raw_message_list[0].strip(" ").rsplit(" ", 1)
                tags_dict = process_tags(tags_raw)
                if tags_dict.get("msg_id") == "raid":
                    for sub in self.subscribers_events:
                        sub(EventType.RAID, RaidEventMessage(**tags_dict))
            else:
                if line.startswith("PING"):
                    pong_host = line.split(" ")[1]
                    self.send(f"PONG {pong_host}")
                elif line.find("NOTICE") > 0 and line.endswith(":Login authentication failed") > 0:
                    gLogger.critical(f"Error authenticating chat with Twitch. {line}")
                    return
                elif not self.has_started:
                    gLogger.info("Chat connection completed")
                    self.has_started = True
