import abc
from typing import List, Optional, Set, Union

from config import Config
from model import User
from user_type import UserType

__all__ = ["ChatComponent"]


class ChatComponent:
    @abc.abstractmethod
    def __init__(self, config: Config):
        pass

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
