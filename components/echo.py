from datetime import datetime
from typing import Any, List, Mapping, Optional, Set, Union

from model import User
from twitch import ChatComponent, UserType

__all__ = ["EchoComponent"]


class EchoComponent(ChatComponent):  # TODO: Change to chat store
    @staticmethod
    def get_id() -> str:
        return "echo"

    @staticmethod
    def get_name() -> str:
        return "Echo"

    @staticmethod
    def get_description() -> str:
        return "This component just prints the chat"

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return None  # To get all the messages without command filtering

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def process_message(self, message: str, user: User, user_types: Set[UserType]) -> bool:
        print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [{user.display_name}] {message}")
        return True

    def process_event(self, event_name: str, payload: Mapping[str, Any]) -> bool:
        user = payload["redemption"]["user"]["display_name"]
        reward_name = payload["redemption"]["reward"]["title"]
        print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [{user}] {event_name}: {reward_name}")
        return True
