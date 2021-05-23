import logging
import time
from typing import Any, List, Mapping, Optional, Union

from network.socket_connector import SocketConnector

from ...model import SceneModel
from ...obs_interface import OBSInterface
from .base.slobs_client import SLOBSClient

__all__ = ["StreamlabsOBS"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class StreamlabsOBS(OBSInterface):
    def __init__(self, host: str, port: int, token: str) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.exit_requested = False
        self.conected = False
        self.waiting_token = False
        self.client: Optional[SLOBSClient] = None
        self.connector: Optional[SocketConnector] = None

    def start_obs_connection(self) -> bool:  # Runs in OBSConnector thread
        if self.conected:
            return True
        try:
            gLogger.info("Trying to connect to OBS")
            self.waiting_token = True
            self.client = SLOBSClient(self.host, self.port, self.token)
            self.client.disconnected_event.connect(self.obs_disconnected)
            self.client.start()
            self.conected = True
            self.waiting_token = False
            gLogger.info("Connected to OBS")
            return True
        except Exception as e:
            if str(e) == "Authentication Failed.":
                gLogger.error("Error authenticating to OBS, please check your configuration")
                while self.waiting_token:
                    time.sleep(1)
            return self.exit_requested
        except Exception:
            time.sleep(1)
            return False

    def obs_disconnected(self):
        self.conected = False
        if self.client:
            try:
                self.client.stop()
                self.client = None
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
        self.token = config["token"]
        self.waiting_token = False
        if self.connector:
            self.connector.set_host(self.host)
            self.connector.set_port(self.port)

    def is_connected(self) -> bool:
        return self.client is not None and self.client.is_alive() is not None and self.client.running and self.conected

    def connect(self) -> None:
        self.exit_requested = False
        self.connector = SocketConnector(self.host, self.port, self.start_obs_connection)
        self.connector.name = "StreamlabsOBSConnector"
        self.connector.start()

    def disconnect(self) -> None:
        self.exit_requested = True
        self.waiting_token = False
        self.conected = False
        if self.connector is not None:
            self.connector.stop()
        if self.client is not None:
            try:
                self.client.stop()
                self.client = None
            except Exception:
                pass

    def get_scenes(self) -> List[SceneModel]:
        if self.client is not None:
            scene_service = self.client.get_scene_service()
            return [SceneModel(name=scene.name) for scene in scene_service.getScenes()]
        return []

    def get_current_scene(self) -> Optional[SceneModel]:
        if self.client is not None:
            scene_service = self.client.get_scene_service()
            scene = scene_service.activeScene()
            return SceneModel(name=scene.name)

    def set_current_scene(self, scene: Union[SceneModel, str]) -> None:
        if isinstance(scene, SceneModel):
            scene_name = scene.name
        else:
            scene_name = scene
        if self.client is not None:
            scene_service = self.client.get_scene_service()
            scenes = scene_service.getScenes()
            for s in scenes:
                if scene_name == s.name:
                    scene_service.makeSceneActive(s.id)

    def set_text_gdi_plus_properties(self, source: str, **properties: Any) -> None:
        if self.client is not None:
            scene_service = self.client.get_scene_service()
            active_scene = scene_service.activeScene()
            node = active_scene.getNodeByName(source)
            if node is not None:
                source_instance = node.getSource()
                if source_instance:
                    form_data = []
                    for prop in properties:
                        form_data.append({"value": f"{properties[prop]}", "name": f"{prop}"})
                    source_instance.setPropertiesFormData(form_data)
