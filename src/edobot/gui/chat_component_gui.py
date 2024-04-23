from abc import abstractmethod
from typing import Any, Optional, Union

import qtawesome as qta
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget

from core.chat_component import ChatComponent

__all__ = ["ChatComponentGUI"]


class ChatComponentMetadata:

    def __init__(self, name: str, description: str, icon: Optional[QIcon] = None, debug: bool = False):
        self.name = name
        self.description = description
        self.icon: QIcon = qta.icon("fa5.question-circle") if icon is None else icon
        self.debug = debug


class ChatComponentGUI(ChatComponent):

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    @abstractmethod
    def get_metadata() -> "ChatComponent.Metadata":
        raise NotImplementedError("Please implement this method")

    def get_config_ui(self) -> Union[QWidget, dict[str, Any], None]:
        return None
