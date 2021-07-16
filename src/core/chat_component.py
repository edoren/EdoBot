from abc import ABC, abstractmethod
from typing import Any, List, Optional, Set, Union, final

import qtawesome as qta
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QWidget

from core.config import Config
from model import EventType, User, UserType
from obs import OBSInterface
from twitch.chat import Chat  # TODO: Replace with ChatWrapper
from twitch.service import Service as TwitchService

__all__ = ["ChatComponent"]


class ChatComponent(ABC):
    class Metadata:
        def __init__(self, name: str, description: str, icon: Optional[QIcon] = None, debug: bool = False):
            self.name = name
            self.description = description
            self.icon: QIcon = qta.icon("fa5.question-circle") if icon is None else icon
            self.debug = debug

    def __init__(self) -> None:
        self.has_started = False
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
    def get_metadata() -> "ChatComponent.Metadata":
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def get_command(self) -> Optional[Union[str, List[str]]]:
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def process_message(self, message: str, user: User, user_types: Set[UserType],
                        metadata: Optional[Any] = None) -> None:
        pass

    @abstractmethod
    def process_event(self, event_type: EventType, metadata: Optional[Any] = None) -> None:
        pass

    def start(self) -> None:
        self.has_started = True

    def stop(self) -> None:
        self.has_started = False

    def get_config_ui(self) -> Union[QWidget, dict[str, Any], None]:
        return None

    def on_config_updated(self, name: str, value: Any) -> None:
        pass
