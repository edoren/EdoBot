import logging
import time
from typing import Any, List, Mapping, Optional, Union

import obswebsocket.events as obs_events
import obswebsocket.requests as obs_requests
from obswebsocket import obsws
from obswebsocket.exceptions import ConnectionFailure
from websocket import WebSocketConnectionClosedException

from network import SocketConnector

from ...model import SceneModel
from ...obs_interface import OBSInterface

__all__ = ["OBSWebSocket"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class OBSWebSocket(OBSInterface):
    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.exit_requested = False
        self.conected = False
        self.waiting_password = False
        self.client: obsws = obsws(self.host, self.port, self.password)
        self.client.register(self.obs_disconnected, obs_events.Exiting)
        self.connector: Optional[SocketConnector] = None

    def start_obs_connection(self) -> bool:  # Runs in OBSConnector thread
        if self.conected:
            return True
        try:
            gLogger.info("Trying to connect to OBS")
            self.client.password = self.password
            self.waiting_password = True
            self.client.connect(self.host, self.port)
            self.client.thread_recv.name = f"OBSWebSocketThread"  # type: ignore
            self.conected = True
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
        self.conected = False
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
        self.connect()  # Start retry loop

    def __del__(self):
        if self.connector is not None:
            self.connector.join()
            self.connector = None

    # Override OBSInterface

    def set_config(self, config: Mapping[str, Any]):
        self.host = config["host"]
        self.port = config["port"]
        self.password = config["password"]
        self.waiting_password = False
        if self.connector:
            self.connector.set_host(self.host)
            self.connector.set_port(self.port)

    def is_connected(self) -> bool:
        return self.client.thread_recv is not None and self.client.thread_recv.running and self.conected

    def connect(self) -> None:
        self.exit_requested = False
        self.connector = SocketConnector(self.host, self.port, self.start_obs_connection)
        self.connector.name = "OBSWebSocketConnector"
        self.connector.start()

    def disconnect(self) -> None:
        self.exit_requested = True
        self.waiting_password = False
        self.conected = False
        if self.connector is not None:
            self.connector.stop()
        if self.client is not None:
            try:
                self.client.disconnect()
            except AttributeError as e:
                pass
            except Exception as e:
                raise e

    def get_scenes(self) -> List[SceneModel]:
        request: obs_requests.GetSceneList = self.client.call(obs_requests.GetSceneList())
        return [SceneModel(name=scene["name"]) for scene in request.getScenes()]

    def get_current_scene(self) -> Optional[SceneModel]:
        request: obs_requests.GetCurrentScene = self.client.call(obs_requests.GetCurrentScene())
        return SceneModel(name=request.getName())

    def set_current_scene(self, scene: Union[SceneModel, str]) -> None:
        if isinstance(scene, SceneModel):
            scene_name = scene.name
        else:
            scene_name = scene
        self.client.call(obs_requests.SetCurrentScene(scene_name))

    def set_text_gdi_plus_properties(self, source: str, **properties: Any) -> None:
        try:
            self.client.call(obs_requests.SetTextGDIPlusProperties(source, **properties))
        except WebSocketConnectionClosedException:
            pass
