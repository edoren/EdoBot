import logging
import socket
import threading
import time
from typing import Callable, Optional

import obswebsocket
import obswebsocket.events as obs_events
import obswebsocket.requests

__all__ = ["OBSWrapper"]

gLogger = logging.getLogger(__name__)


class OBSConnector(threading.Thread):
    def __init__(self, host: str, port: int, callback: Callable[[], None]):
        super().__init__(name=f"{self.__class__.__name__}Thread")
        self.host = host
        self.port = port
        self.callback = callback
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        gLogger.info("Waiting OBS connection...")
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((self.host, self.port))
                if result == 0:
                    self.running = False
                    self.callback()
            except socket.error:
                time.sleep(5)


class OBSWrapper:
    def __init__(self, obs_port: int, obs_password: str):
        self.obs_host = "localhost"
        self.obs_port = obs_port
        self.obs_password = obs_password
        self.obs_client = obswebsocket.obsws(self.obs_host, self.obs_port,
                                             self.obs_password)
        self.obs_client.register(self.obs_disconnected, obs_events.Exiting)
        self.obs_is_connected = False
        self.obs_connector: Optional[OBSConnector] = None

    def connect(self) -> None:
        self.obs_connector = OBSConnector(self.obs_host, self.obs_port,
                                          self.start_obs_connection)
        self.obs_connector.start()

    def disconnect(self) -> None:
        self.obs_is_connected = False
        if self.obs_connector is not None:
            self.obs_connector.stop()
            self.obs_connector.join()
        if self.obs_client is not None:
            try:
                self.obs_client.disconnect()
            except Exception:
                pass

    def get_client(self) -> obswebsocket.obsws:
        return self.obs_client

    def start_obs_connection(self):
        if self.obs_is_connected:
            return
        try:
            self.obs_client.connect()
            self.obs_client.thread_recv.name = f"OBSClientThread"  # type: ignore
            self.obs_is_connected = True
        except Exception:
            self.connect()  # Start retry loop

    def obs_disconnected(self, message):
        self.obs_is_connected = False
        try:
            self.obs_client.disconnect()
        except Exception:
            pass
        self.connect()  # Start retry loop
