import logging
from typing import Callable, List, Optional

from network import WebSocket
from twitch.irc_tags import PrivateMsgTags

__all__ = ["Chat", "PrivateMsgTags"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class Chat(WebSocket):
    MessageCallable = Callable[[str, PrivateMsgTags, str], None]

    def __init__(self, nickname: str, password: str, channel_name: str):
        super().__init__("wss://irc-ws.chat.twitch.tv", timeout=1)

        self.nickname = nickname.lower()
        self.password = password
        self.channel_name = channel_name.lower()
        self.last_ping_time: Optional[float] = None
        self.has_started = False
        self.subscribers: List[Chat.MessageCallable] = []

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

    def send_message(self, message: str) -> None:
        self.send(f"PRIVMSG #{self.channel_name} :{message}")

    def handle_message(self, message: str):
        lines = message.strip("\r\n").split("\r\n")
        for line in lines:
            if line.find("PRIVMSG") > 0:
                gLogger.debug(line)

                raw_message_list = line.rsplit("PRIVMSG", 1)

                tags_raw, sender_raw = raw_message_list[0].strip(" ").rsplit(" ", 1)

                tags_dict = {}
                for key_value in tags_raw.lstrip("@").split(";"):
                    key, value = key_value.split("=", 1)
                    if key not in ["subscriber", "turbo", "user-type"]:  # Ignore deprecated tags
                        tags_dict[key.replace("-", "_")] = value
                tags = PrivateMsgTags(**tags_dict)

                sender = sender_raw.split("!")[0].lstrip(":")

                if not tags.display_name:  # display_name might be empty
                    tags.display_name = sender

                _, text = raw_message_list[1].split(":", 1)  # channel, text

                sender = sender.strip("# ")
                text = text.strip(" ")
                for sub in self.subscribers:
                    sub(sender, tags, text)
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
