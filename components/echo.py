from typing import List, Optional, Set, Union

from component import TwitchChatComponent
from config import Config
from model import User
from user_type import UserType

__all__ = ["EchoComponent"]


class EchoComponent(TwitchChatComponent):
    def __init__(self, config: Config):
        pass

    @staticmethod
    def get_name() -> str:
        return "echo"

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return None

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def process_message(self, message: str, user: User, user_flags: Set[UserType]) -> bool:
        print(f"[{user.display_name}] {message}")
        return True
