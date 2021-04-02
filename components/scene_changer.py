import logging
from typing import Any, List, Mapping, Optional, Set, Union

import obswebsocket.requests as obs_requests

from model import User
from twitch import ChatComponent, UserType

gLogger = logging.getLogger("edobot.components.scene_changer")

__all__ = ["SceneChangerComponent"]


class SceneChangerComponent(ChatComponent):
    @staticmethod
    def get_id() -> str:
        return "scene_changer"

    @staticmethod
    def get_name() -> str:
        return "Scene Changer"

    @staticmethod
    def get_description() -> str:
        return "This component allows Mods change the OBS scenes"

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return self.command

    def start(self) -> None:
        self.command = ~self.config["command"]
        if self.command is None:
            self.command = "scene"
            self.config["command"] = self.command

    def stop(self) -> None:
        pass

    def process_message(self, message: str, user: User, user_types: Set[UserType]) -> bool:
        if self.obs_client.thread_recv is None or not self.obs_client.thread_recv.running:
            return False

        if UserType.MODERATOR in user_types:
            transition_matrix = self.__get_transitions()

            scenes_request: obs_requests.GetSceneList = self.obs_client.call(obs_requests.GetSceneList())
            scenes: List[Mapping[str, Any]] = scenes_request.getScenes()

            # Find a suitable scene target name
            target_scene = None
            for scene in scenes:
                if scene["name"].lower() == message.lower():
                    target_scene = scene["name"]

            if target_scene is not None:
                current_scene = scenes_request.getCurrentScene()
                if current_scene in transition_matrix:
                    if target_scene in transition_matrix[current_scene]:
                        gLogger.info(f"[{user.display_name}] Transitioning: {current_scene} -> {target_scene}")
                        self.obs_client.call(obs_requests.SetCurrentScene(target_scene))
                else:
                    gLogger.error(f"Error: Scene '{current_scene}' not found in transition matrix")

        return True

    def process_event(self, event_name: str, payload: Mapping[str, Any]) -> bool:
        return True

    def __get_transitions(self) -> Any:
        if self.obs_client is not None and ~self.config["transitions"] is None:
            scenes_request: obs_requests.GetSceneList = self.obs_client.call(obs_requests.GetSceneList())
            scenes: List[Mapping[str, Any]] = scenes_request.getScenes()
            transition_matrix = {}
            for scene in scenes:
                transition_matrix[scene["name"]] = []
            self.config["transitions"] = transition_matrix
        return ~self.config["transitions"]
