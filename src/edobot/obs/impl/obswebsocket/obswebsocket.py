import logging
import time
from typing import Any, List, Mapping, Optional, Union

import obsws_python as obs

from edobot.network import SocketConnector
from edobot.obs.model import SceneModel
from edobot.obs.obs_interface import OBSInterface

__all__ = ["OBSWebSocket"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class OBSWebSocket(OBSInterface):
    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.exit_requested = False
        self.conected = False
        self.waiting_password = True
        self.client: Optional[obs.ReqClient] = None
        self.connector: Optional[SocketConnector] = None

    def start_obs_connection(self) -> bool:  # Runs in OBSConnector thread
        if self.conected:
            return True
        try:
            gLogger.info("Trying to connect to OBS")
            self.client: Optional[obs.ReqClient] = obs.ReqClient(host=self.host, port=self.port, password=self.password)
            version = self.client.get_version()
            if not hasattr(version, "obs_version"):
                return False
            self.waiting_password = False
            self.conected = True
            gLogger.info("Connected to OBS")
            return True
        except Exception as e:
            gLogger.error("Error authenticating to OBS, please check your configuration. [" + str(e) + "]")
            while self.waiting_password:
                time.sleep(1)
            return self.exit_requested

    # TODO: Handle random disconnection
    # def obs_disconnected(self, message):
    #     self.conected = False
    #     if self.client:
    #         try:
    #             del self.client
    #             self.client = None
    #         except Exception:
    #             pass
    #     self.connect()  # Start retry loop

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
        if self.client is None:
            return False
        try:
            version = self.client.get_version()
            if not hasattr(version, "obs_version"):
                return False
            return True
        except Exception:
            if self.client is not None:
                self.disconnect()
                self.connect()
            return False

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
                del self.client
                self.client = None
            except AttributeError as e:
                pass
            except Exception as e:
                raise e

    def get_scenes(self) -> List[SceneModel]:
        if not self.is_connected():
            return []
        try:
            response = self.client.get_scene_list()
            return [SceneModel(name=scene["sceneName"]) for scene in response.scenes]
        except Exception:
            pass
        return []

    def get_current_scene(self) -> Optional[SceneModel]:  # get_current_program_scene
        if not self.is_connected():
            return None
        try:
            response = self.client.get_current_program_scene()
            return SceneModel(name=response.currentProgramSceneName)
        except Exception:
            pass
        return None

    def set_current_scene(self, scene: Union[SceneModel, str]) -> None:
        if not self.is_connected():
            return
        if isinstance(scene, SceneModel):
            scene_name = scene.name
        else:
            scene_name = scene
        try:
            self.client.set_current_program_scene(scene_name)
        except Exception:
            pass

    def set_text_gdi_plus_properties(self, source: str, **properties: Any) -> None:
        if not self.is_connected():
            return
        try:
            settings = self.client.get_input_settings(source)
            if settings is not None and settings.input_kind == "text_gdiplus_v2":
                self.client.set_input_settings(source, {"text": properties["text"]}, True)
        except Exception:
            pass
