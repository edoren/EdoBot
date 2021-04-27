import abc
import logging
import re
import sys
import threading
import time
from typing import Optional, final

import websocket

__any__ = ["WebSocket"]

gLogger = logging.getLogger(f"edobot.{__name__}")
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
        self.connected = False

        self.socket: websocket.WebSocket = websocket.WebSocket()
        self.socket.settimeout(timeout)
        self.lock = threading.Lock()

    @abc.abstractmethod
    def handle_message(self, message: str) -> None:
        pass

    def connect(self) -> None:
        try:
            self.socket.connect(self.url)
            self.connected = True
        except websocket.WebSocketException:
            self.connected = False
        except Exception as e:
            gLogger.error(f"Unknown error: {e}")
            self.connected = False

    def disconnect(self) -> None:
        try:
            self.socket.close()
        except websocket.WebSocketException:
            pass
        self.connected = False

    def stop(self) -> None:
        if self.is_alive():
            self.running = False
        self.disconnect()

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
        reconnect_time = 1
        while self.running:
            message = ""
            try:
                self.ping()
                with self.lock:
                    message: str = self.socket.recv()
                if message:
                    self.handle_message(message)
            except (OSError, websocket.WebSocketConnectionClosedException) as e:
                gLogger.error(f"Connection failed for endpoint {self.host}: {e}")
                self.connected = False
                if self.running:
                    gLogger.info(f"Retrying connection in {reconnect_time}s")
                    time.sleep(reconnect_time)
                    self.connect()
                    if not self.connected:
                        reconnect_time *= 2
                    else:
                        reconnect_time = 1
            except websocket.WebSocketTimeoutException:
                continue

    def __del__(self):
        if self.is_alive():
            self.join()
