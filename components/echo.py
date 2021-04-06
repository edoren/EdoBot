import logging
from typing import Any, List, Mapping, Optional, Set, Union

from model import User
from twitch import ChatComponent, UserType

__all__ = ["EchoComponent"]

gLogger = logging.getLogger("edobot.components.echo")


class EchoComponent(ChatComponent):  # TODO: Change to chat store
    @staticmethod
    def get_id() -> str:
        return "echo"

    @staticmethod
    def get_name() -> str:
        return "Echo"

    @staticmethod
    def get_description() -> str:
        return "This component just displays the chat in the logs"

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return None  # To get all the messages without command filtering

    def start(self) -> None:
        gLogger.info("Starting Echo component")
        super().start()

    def stop(self) -> None:
        gLogger.info("Stopping Echo component")
        super().stop()

    def process_message(self, message: str, user: User, user_types: Set[UserType]) -> bool:
        gLogger.info((f"[{user.display_name}] {message}"))
        return True

    def process_event(self, event_name: str, payload: Mapping[str, Any]) -> bool:
        user = payload["redemption"]["user"]["display_name"]
        reward_name = payload["redemption"]["reward"]["title"]
        gLogger.info((f"[{user}] {event_name}: {reward_name}"))
        return True
