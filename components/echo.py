import logging
from typing import Any, List, Optional, Set, Union

import twitch
from core import ChatComponent
from model import EventType, User, UserType

__all__ = ["EchoComponent"]

gLogger = logging.getLogger("edobot.components.echo")


class EchoComponent(ChatComponent):
    @staticmethod
    def get_id() -> str:
        return "echo"

    @staticmethod
    def get_metadata() -> ChatComponent.Metadata:
        return ChatComponent.Metadata(name="Echo", description="Displays the chat in the logs", icon=None, debug=True)

    def get_command(self) -> Optional[Union[str, List[str]]]:
        return None  # To get all the messages without command filtering

    def start(self) -> None:
        gLogger.info("Starting Echo component")
        super().start()

    def stop(self) -> None:
        gLogger.info("Stopping Echo component")
        super().stop()

    def process_message(self,
                        message: str,
                        user: User,
                        user_types: Set[UserType],
                        metadata: Optional[Any] = None) -> None:
        gLogger.info((f"[{user.display_name}] {message}"))

    def process_event(self, event_type: EventType, metadata: Any) -> None:
        if event_type == event_type.REWARD_REDEEMED:
            event_data: twitch.ChannelPointsEventMessage = metadata
            gLogger.info((f"[{event_data.redemption.user.display_name}] {event_type}: "
                          f"{event_data.redemption.reward.title}"))
