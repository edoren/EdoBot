import logging
import socket
import threading
import time
from typing import Callable

gLogger = logging.getLogger(f"edobot.{__name__}")

__all__ = ["SocketConnector"]


class SocketConnector(threading.Thread):
    def __init__(self, host: str, port: int, retry_connection_cb: Callable[[], bool]):
        super().__init__(name=f"{self.__class__.__name__}Thread")
        self.host = host
        self.port = port
        self.retry_connection_cb = retry_connection_cb
        self.running = True

    def set_host(self, host: str):
        self.host = host

    def set_port(self, port: int):
        self.port = port

    def stop(self):
        self.running = False

    def run(self):
        gLogger.info(f"Waiting connection from {self.host}:{self.port}")
        while self.running:
            try:
                if self.host and self.port:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    result = sock.connect_ex((self.host, self.port))
                    if result == 0:
                        self.running = not self.retry_connection_cb()
            except socket.error:
                time.sleep(1)
