import logging
import socket
import threading
import time
from typing import Optional

import obswebsocket.events as obs_events
import obswebsocket.requests  # type: ignore
from obswebsocket.exceptions import ConnectionFailure
from obswebsocket import obsws

__all__ = ["OBSWrapper"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class OBSConnector(threading.Thread):
    def __init__(self, parent: "OBSWrapper"):
        super().__init__(name=f"{self.__class__.__name__}Thread")
        self.parent = parent
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        gLogger.info("Waiting OBS connection...")
        while self.running:
            try:
                if self.parent.host and self.parent.port:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    result = sock.connect_ex((self.parent.host, self.parent.port))
                    if result == 0:
                        self.running = not self.parent.start_obs_connection()
            except socket.error:
                time.sleep(1)


class OBSWrapper:
    def __init__(self):
        self.host = "localhost"
        self.port = 4444
        self.password = "changeme"
        self.exit_requested = False
        self.is_connected = False
        self.waiting_password = False
        self.client: obsws = obsws(self.host, self.port, self.password)
        self.client.register(self.obs_disconnected, obs_events.Exiting)
        self.connector: Optional[OBSConnector] = None

    def set_config(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.waiting_password = False

    def connect(self) -> None:
        self.exit_requested = False
        self.connector = OBSConnector(self)
        self.connector.start()

    def disconnect(self) -> None:
        self.exit_requested = True
        self.waiting_password = False
        self.is_connected = False
        if self.connector is not None:
            self.connector.stop()
            self.connector.join()
        if self.client is not None:
            try:
                self.client.disconnect()
            except Exception:
                pass

    def get_client(self) -> obsws:
        return self.client

    def start_obs_connection(self) -> bool:  # Runs in OBSConnector thread
        if self.is_connected:
            return True
        try:
            gLogger.info("Trying to connect to OBS")
            self.client.password = self.password
            self.waiting_password = True
            self.client.connect(self.host, self.port)
            self.client.thread_recv.name = f"OBSClientThread"  # type: ignore
            self.is_connected = True
            self.waiting_password = False
            gLogger.info("Connected to OBS")
            return True
        except ConnectionFailure as e:
            if str(e) == "Authentication Failed.":
                gLogger.error("Error authenticating to OBS, please check your configuration")
                while self.waiting_password:
                    time.sleep(1)
            return self.exit_requested
        except Exception:
            time.sleep(1)
            return False

    def obs_disconnected(self, message):
        self.is_connected = False
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
        self.connect()  # Start retry loop
