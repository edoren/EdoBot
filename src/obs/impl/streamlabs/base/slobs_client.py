import json
import logging
import threading
import time
from typing import Any, MutableMapping

from network.websocket import WebSocket
from core.signal import Signal

from ..services.scenes_service import ScenesService
from .json_rpc_message import JSONRPCMessage

gLogger = logging.getLogger(f"edobot.{__name__}")


class SLOBSClient(WebSocket):
    def __init__(self, host: str, port: int, token: str) -> None:
        super().__init__(f"ws://{host}:{port}/api/websocket", 10)

        self.set_retry_enabled(False)

        self.token = token

        self.request_id_lock = threading.Lock()
        self.request_id = 1
        self.answers: MutableMapping[int, Any] = {}

        self.api_busy_lock = threading.Lock()

        self.disconnected_event = Signal()

    def start(self) -> None:
        super().start()
        self.connect()

    def stop(self) -> None:
        super().stop()
        super().join()

    def send_and_wait_jsonrpc(self, message: JSONRPCMessage, optional: bool = True) -> Any:
        while self.running:
            with self.api_busy_lock:
                super().send(message.json())
            response = self.__wait_message(message.get_id())
            if optional or response is not None:
                return response

    def connect(self) -> None:
        if not self.connected:
            gLogger.info("Starting SLOBS connection...")
            self.has_started = False
            super().connect()
            if self.connected:
                # Authenticate
                data = {"resource": "TcpServerService", "args": [self.token]}
                message = JSONRPCMessage("auth", data)
                auth_response = self.send_and_wait_jsonrpc(message)
                if not isinstance(auth_response, bool):
                    raise Exception("Authentication Failed.")

    def __wait_message(self, message_id: int) -> Any:
        timeout = time.time() + 60  # Timeout = 60s
        while time.time() < timeout and self.running:
            if self.api_busy_lock.locked():
                return None
            if message_id in self.answers:
                data = self.answers.pop(message_id)
                result = data["result"]
                return result
            time.sleep(0.025)
        if self.running:
            raise Exception(f"No answer for message {message_id}")

    def handle_message(self, message: str) -> None:
        responses = message.strip("\n").split("\n")
        # print("".join(responses))
        for response in responses:
            data = json.loads(response)
            if "error" in data:
                error = data["error"]
                if "API server is busy" in error["message"]:
                    with self.api_busy_lock:
                        time.sleep(2)
            if "id" in data:
                self.answers[data["id"]] = data
            else:
                result = data["result"]
                if isinstance(result, dict) and result.get("_type") == "EVENT":
                    pass  # Handle subscription

    def connection_closed(self) -> None:
        self.disconnected_event.emit()

    def get_scene_service(self) -> ScenesService:
        scene_service = getattr(self, "scene_service", None)
        if scene_service is None:
            self.scene_service = ScenesService(self)
        return self.scene_service
