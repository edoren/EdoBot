import abc
import threading
from typing import Optional, final

from ws4py.client.threadedclient import WebSocketClient


class WebSocket(WebSocketClient):
    def __init__(self, url: str) -> None:
        WebSocketClient.__init__(self, url)
        self.is_waiting_message = False
        self.sleep_event = threading.Event()
        self.last_message_data: Optional[bytes] = None

    def opened(self):
        pass

    def closed(self, code, reason=None):
        pass

    @final
    def received_message(self, message):
        if self.is_waiting_message and not self.sleep_event.is_set():
            self.last_message_data = message.data
            self.is_waiting_message = False
            self.sleep_event.set()
            return
        self.handle_message(message.data)

    @abc.abstractmethod
    def handle_message(self, message: bytes):
        pass

    @final
    def send_and_recv(self, payload, timeout=None) -> bytes:
        self.is_waiting_message = True
        super().send(payload)
        self.sleep_event.wait(timeout)
        self.sleep_event.clear()
        if self.last_message_data is not None:
            message = self.last_message_data
            self.last_message_data = None
            return message
        else:
            return bytes()
