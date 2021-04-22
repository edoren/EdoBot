from abc import ABC, abstractmethod
from typing import Any, List, Optional, Set, Union, final

import obswebsocket
from PySide2.QtWidgets import QWidget

from model import User, UserType
from twitch.chat import Chat  # TODO: Replace with ChatWrapper
from twitch.service import Service as TwitchService

from .config import Config

__all__ = ["ChatComponent"]


class ChatComponent(ABC):
    def __init__(self) -> None:
        self.has_started = False
        super().__init__()

    @final
    def config_component(self, config: Config, obs_client: obswebsocket.obsws,
                         chat: Chat, twitch: TwitchService) -> None:
        self.config = config
        self.obs_client = obs_client
        self.chat = chat
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
    def process_message(self, message: str, user: User,
                        user_types: Set[UserType], metadata: Optional[Any] = None) -> None:
        pass

    @abstractmethod
    def process_event(self, event_name: str, metadata: Optional[Any] = None) -> None:
        pass

    def start(self) -> None:
        self.has_started = True

    def stop(self) -> None:
        self.has_started = False

    def is_obs_connected(self) -> bool:
        return (hasattr(self, "obs_client") and
                self.obs_client is not None and
                self.obs_client.thread_recv is not None and
                self.obs_client.thread_recv.running)

    def get_config_something(self) -> Union[QWidget, dict[str, Any], None]:
        return None

    def on_config_updated(self, name: str, value: Any) -> None:
        pass