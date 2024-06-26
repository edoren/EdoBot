import logging
from typing import Any, List, Optional, Set, Union, override

from edobot.core import Component
from edobot.model import EventType, User, UserType
from edobot.services import twitch

__all__ = ["EchoComponent"]

gLogger = logging.getLogger("edobot.components.echo")


class EchoComponent(Component):
    @staticmethod
    @override
    def get_id() -> str:
        return "echo"

    @staticmethod
    @override
    def get_metadata() -> Component.Metadata:
        return Component.Metadata(name="Echo", description="Displays the chat in the logs", icon=None, debug=True)

    @override
    def get_cmmand(self) -> str | List[str] | None:
        return None  # To get all the messages without command filtering

    @override
    def start(self) -> None:
        gLogger.info("Starting Echo component")
        super().start()

    @override
    def stop(self) -> None:
        gLogger.info("Stopping Echo component")
        super().stop()

    @override
    def process_message(
        self, message: str, user: User, user_types: Set[UserType], metadata: Optional[Any] = None
    ) -> None:
        gLogger.info((f"[{user.display_name}] {message}"))

    @override
    def process_event(self, event_type: EventType, metadata: Any) -> None:
        if event_type == event_type.REWARD_REDEEMED:
            points_event: twitch.events.ChannelPointsEvent = metadata
            gLogger.info(
                (
                    f"[{points_event.redemption.user.display_name}] {event_type}: "
                    f"{points_event.redemption.reward.title}"
                )
            )
        if event_type == event_type.SUBSCRIPTION:
            sub_event: twitch.events.SubscriptionEvent = metadata
            if sub_event.is_gift:
                gLogger.info(
                    f"[{sub_event.display_name}]: Sub Gift to {sub_event.recipient_display_name} - "
                    f"{sub_event.sub_plan_name} ({sub_event.sub_plan})"
                )
            else:
                gLogger.info(
                    f"[{sub_event.display_name}]: Subscribed - {sub_event.sub_plan_name} ({sub_event.sub_plan})"
                )
