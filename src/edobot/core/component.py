from abc import ABC, abstractmethod
from typing import Any, List, Set, Union, final

import qtawesome as qta
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget

from edobot.core.config import Config
from edobot.model import EventType, User, UserType
from edobot.obs import OBSInterface
from edobot.services.twitch import Chat  # TODO: Replace with ChatWrapper
from edobot.services.twitch import Service as TwitchService

__all__ = ["Component"]


class Component(ABC):
    class Metadata:
        def __init__(self, name: str, description: str, icon: QIcon | None = None, debug: bool = False):
            self.name = name
            self.description = description
            self.icon: QIcon = qta.icon("fa5.question-circle") if icon is None else icon
            self.debug = debug

    def __init__(self) -> None:
        super().__init__()

    @final
    def config_component(self, config: Config, obs: OBSInterface, chat: Chat, twitch: TwitchService) -> None:
        self.config = config
        self.obs = obs
        self.chat = chat
        self.twitch = twitch

    @staticmethod
    @abstractmethod
    def get_id() -> str:
        raise NotImplementedError("Please implement this method")

    @staticmethod
    @abstractmethod
    def get_metadata() -> "Component.Metadata":
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def get_command(self) -> str | List[str] | None:
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def process_message(self, message: str, user: User, user_types: Set[UserType], metadata: Any | None = None) -> None:
        pass

    @abstractmethod
    def process_event(self, event_type: EventType, metadata: Any | None = None) -> None:
        pass

    @abstractmethod
    def start(self) -> bool:
        return False

    @abstractmethod
    def stop(self) -> None:
        pass

    def get_config_ui(self) -> QWidget | dict[str, Any] | None:
        return None

    def on_config_updated(self, name: str, value: Any) -> None:
        pass
