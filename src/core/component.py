import abc
from typing import Any, List, Mapping, Optional, Set, Union, final

import obswebsocket

from model import User

from .config import Config
from .user_type import UserType

__all__ = ["ChatComponent"]


class ChatComponent(abc.ABC):
    @final
    def config_component(self, config: Config, obs_client: obswebsocket.obsws) -> None:
        self.config = config
        self.obs_client = obs_client

    @staticmethod
    @abc.abstractmethod
    def get_name() -> str:
        pass

    @abc.abstractmethod
    def get_command(self) -> Optional[Union[str, List[str]]]:
        pass

    @abc.abstractmethod
    def start(self) -> None:
        pass

    @abc.abstractmethod
    def stop(self) -> None:
        pass

    @abc.abstractmethod
    def process_message(self, message: str, user: User, user_types: Set[UserType]) -> bool:
        pass

    @abc.abstractmethod
    def process_event(self, event_name: str, payload: Mapping[str, Any]) -> bool:
        pass
