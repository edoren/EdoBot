import abc
import logging
import re
import socket
import sys
import threading
import time
from typing import Optional, final

import websocket

__any__ = ["WebSocket"]

gLogger = logging.getLogger(__name__)
gWebSocketRegex = re.compile(r"^(wss?:\/\/)([0-9]{1,3}(?:\.[0-9]{1,3}){3}|[a-zA-Z0-9-\.]+)(?::([0-9]{1,5}))?")


class WebSocket(threading.Thread, abc.ABC):
    def __init__(self, url: str, timeout: Optional[float] = None) -> None:
        super().__init__(name=f"{self.__class__.__name__}Thread")

        self.url = url

        result = gWebSocketRegex.search(url)
        if result is None:
            gLogger.critical(f"Error parsing WebSocket url: {url}")
            sys.exit(-1)
        self.host = result.group(2)
        self.port = int(result.group(3) or 443 if result.group(1) == "wss://" else 80)

        self.running = True
        self.reconnecting = False

        self.socket: websocket.WebSocket = websocket.WebSocket()
        self.socket.settimeout(timeout)
        self.lock = threading.Lock()

    @abc.abstractmethod
    def handle_message(self, message: str) -> None:
        pass

    def connect(self, retry: bool = False) -> None:
        try:
            self.socket.connect(self.url)
        except websocket.WebSocketException:
            if retry:
                self.reconnecting = True

    def disconnect(self) -> None:
        try:
            self.running = False
            self.reconnecting = False
            self.socket.close()
        except websocket.WebSocketException:
            pass

    def ping(self) -> None:
        pass

    @final
    def send(self, message: str):
        with self.lock:
            self.socket.send(message)

    @final
    def send_and_recv(self, message: str, timeout: Optional[float] = None) -> str:
        try:
            with self.lock:
                old_timeout: float = self.socket.gettimeout()
                self.socket.settimeout(timeout)
                self.socket.send(message)
                response: str = self.socket.recv()
                self.socket.settimeout(old_timeout)
            return response
        except websocket.WebSocketException:
            return ""

    @final
    def run(self):
        while self.running:
            message = ""
            try:
                if not self.reconnecting:
                    self.ping()
                    with self.lock:
                        message: str = self.socket.recv()
                    if message:
                        self.handle_message(message)
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    result = sock.connect_ex((self.host, self.port))
                    if result == 0:
                        self.reconnecting = False
                        self.connect()
            except websocket.WebSocketConnectionClosedException as e:
                gLogger.error(f"Error receiving data: {e}")
                if self.running:
                    if self.reconnecting:
                        time.sleep(5)
            except websocket.WebSocketTimeoutException:
                continue
            except OSError as e:
                if self.running:
                    raise e
