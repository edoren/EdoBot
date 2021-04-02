from abc import ABC, abstractmethod
from typing import Any, List, Mapping, Optional, Set, Union, final

import obswebsocket
from PySide2.QtWidgets import QWidget

from core.config import Config
from model import User
from twitch.service import Service as TwitchService

from .user_type import UserType

__all__ = ["ChatComponent"]


class ChatComponent(ABC):
    @final
    def config_component(self, config: Config, obs_client: obswebsocket.obsws, twitch: TwitchService) -> None:
        self.config = config
        self.obs_client = obs_client
        self.twitch = twitch

    @staticmethod
    @abstractmethod
    def get_id() -> str:
        pass

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        pass

    @staticmethod
    @abstractmethod
    def get_description() -> str:
        pass

    @abstractmethod
    def get_command(self) -> Optional[Union[str, List[str]]]:
        pass

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def process_message(self, message: str, user: User, user_types: Set[UserType]) -> bool:
        pass

    @abstractmethod
    def process_event(self, event_name: str, payload: Mapping[str, Any]) -> bool:
        pass

    def get_config_something(self) -> Union[QWidget, dict[str, Any], None]:
        pass

    def on_config_updated(self, name: str, value: Any) -> None:
        pass
