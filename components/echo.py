from datetime import datetime
from typing import List, Optional, Set, Union

from core import ChatComponent, Config, UserType
from model import User

__all__ = ["EchoComponent"]


class EchoComponent(ChatComponent):
    def __init__(self, config: Config):
        pass

    @staticmethod
    def get_name() -> str:
        return "echo"

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return None  # To get all the messages without command filtering

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def process_message(self, message: str, user: User, user_types: Set[UserType]) -> bool:
        print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [{user.display_name}] {message}")
        return True
