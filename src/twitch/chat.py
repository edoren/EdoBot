import logging
from typing import Callable, List, Optional

from core import WebSocket

__all__ = ["Chat"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class Chat(WebSocket):
    MessageCallable = Callable[[str, str], None]

    def __init__(self, nickname: str, password: str, channel_name: str):
        super().__init__("wss://irc-ws.chat.twitch.tv", timeout=1)

        self.nickname = nickname
        self.password = password
        self.channel_name = channel_name
        self.last_ping_time: Optional[float] = None
        self.has_started = False
        self.subscribers: List[Chat.MessageCallable] = []

    def start(self) -> None:
        gLogger.info("Starting Chat connection...")
        self.connect()
        self.send(f"PASS oauth:{self.password}")
        self.send(f"NICK {self.nickname}")
        self.send(f"JOIN #{self.channel_name}")
        super().start()

    def stop(self) -> None:
        self.disconnect()

    def subscribe(self, subscriber: MessageCallable):
        self.subscribers.append(subscriber)

    def send_message(self, message: str) -> None:
        self.send(f"PRIVMSG #{self.channel_name} :{message}")

    def handle_message(self, message: str):
        lines = message.strip("\r\n").split("\r\n")

        for line in lines:
            if line.find("PRIVMSG") > 0:
                raw_message_list = line.split("PRIVMSG", 1)
                sender = raw_message_list[0].split("!")[0].lstrip(":")
                _, text = raw_message_list[1].split(":", 1)  # channel, text
                sender = sender.strip("# ")
                text = text.strip(" ")
                for sub in self.subscribers:
                    sub(sender, text)
            else:
                if line.startswith("PING"):
                    pong_host = line.split(" ")[1]
                    self.send(f"PONG {pong_host}")
                elif line.find("NOTICE") > 0 and line.endswith(":Login authentication failed") > 0:
                    gLogger.critical(f"Error authenticating chat with Twitch. {line}")
                    return
                elif not self.has_started:
                    gLogger.info("Chat connection started")
                    self.has_started = True
