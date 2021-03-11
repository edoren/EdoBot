import getpass
import logging
import socket
import threading
import time
from typing import Callable, List, Optional, Set

import obswebsocket
import obswebsocket.events
import obswebsocket.requests

from component import TwitchChatComponent
from config import Config
from model import User
from user_type import UserType

gLogger = logging.getLogger("me.edoren.edobot.components.scene_changer")

__all__ = ["TwitchChatComponent"]


class OBSConnector(threading.Thread):
    def __init__(self, host: str, port: int, callback: Callable):
        super().__init__()
        self.host = host
        self.port = port
        self.callback = callback
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((self.host, self.port))
                if result == 0:
                    self.running = False
                    self.callback()
            except socket.error:
                time.sleep(5)


class SceneChangerComponent(TwitchChatComponent):  # threading.Thread
    def __init__(self, config: Config):
        self.config = config
        self.obs_connector: Optional[OBSConnector] = None
        self.obs_is_connected = False

        self.command = ~self.config["command"]

        self.obs_host = "localhost"
        self.obs_port = ~self.config["obswebsocket"]["port"]
        self.obs_password = ~self.config["obswebsocket"]["password"]

        if self.command is None:
            print("----- Scene Changer config -----")
            self.command = input("Chat command [scene]: ")
            if self.command == "":
                self.command = "scene"
            while True:
                try:
                    self.obs_port = int(input("OBS port [4444]: ") or 4444)
                    break
                except ValueError:
                    print("Please input a number or just leave it blank")
            self.obs_password = getpass.getpass("OBS password: ")

            self.config["command"] = self.command
            self.config["obswebsocket"]["port"] = self.obs_port
            self.config["obswebsocket"]["password"] = self.obs_password

        self.obs_client = obswebsocket.obsws("localhost", self.obs_port, self.obs_password)
        self.obs_client.register(self.obs_disconnected, obswebsocket.events.Exiting)

    @staticmethod
    def get_name() -> str:
        return "scene_changer"

    def get_command(self) -> str:
        return self.command

    def start(self) -> None:
        self.obs_connector = OBSConnector(self.obs_host, self.obs_port,
                                          self.start_obs_connection)
        self.obs_connector.start()

    def start_obs_connection(self):
        try:
            self.obs_client.connect()
            self.obs_is_connected = True
        except Exception:
            self.start()  # Start retry loop
        if ~self.config["transitions"] is None:
            scenes_request = self.obs_client.call(obswebsocket.requests.GetSceneList())
            scenes = scenes_request.getScenes()
            transition_matrix = {}
            for scene in scenes:
                transition_matrix[scene["name"]] = []
            self.config["transitions"] = transition_matrix

    def stop(self) -> None:
        self.obs_is_connected = False
        if self.obs_connector is not None:
            self.obs_connector.stop()
        if self.obs_client is not None:
            try:
                self.obs_client.disconnect()
            except Exception:
                pass

    def obs_disconnected(self, message):
        self.obs_is_connected = False
        try:
            self.obs_client.disconnect()
        except Exception:
            pass
        self.start()  # Start retry loop

    def process_command(self, args: List[str], user: User, user_flags: Set[UserType]) -> bool:
        if len(args) == 0 or not self.obs_is_connected:
            return False

        if UserType.MODERATOR in user_flags:
            transition_matrix = ~self.config["transitions"]
            scenes_request = self.obs_client.call(obswebsocket.requests.GetSceneList())
            scenes = scenes_request.getScenes()

            # Find a suitable scene target name
            target_scene = None
            for scene in scenes:
                if scene["name"].lower() == args[0].lower():
                    target_scene = scene["name"]

            if target_scene is not None:
                current_scene = scenes_request.getCurrentScene()
                if current_scene in transition_matrix:
                    if target_scene in transition_matrix[current_scene]:
                        gLogger.info(f"[{user.display_name}] Transitioning: {current_scene} -> {target_scene}")
                        self.obs_client.call(obswebsocket.requests.SetCurrentScene(target_scene))
                else:
                    gLogger.error(f"Error: Scene '{current_scene}' not found in transition matrix")

        return True


if __name__ == "__main__":
    def set_interval(func, sec):
        def func_wrapper():
            set_interval(func, sec)
            func()
        t = threading.Timer(sec, func_wrapper)
        t.start()
        return t
