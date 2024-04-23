import json
import logging
from enum import Enum
from typing import Any, Callable, List, Union

from edobot.model import EventType
from edobot.network import WebSocket

from .eventsub_events.bits_badge_event import BitsBadgeEvent
from .eventsub_events.bits_event import BitsEvent, BitsEventMeta
from .eventsub_events.channel_points_event import ChannelPointsEvent
from .eventsub_events.subscription_event import SubscriptionEvent
from .service import Service

__all__ = ["EventSub"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class EventSubEventType(Enum):
    BITS_EVENT = "channel-bits-events-v2"
    BITS_BADGE_EVENT = "channel-bits-badge-unlocks"
    CHANNEL_POINTS_EVENT = "channel-points-channel-v1"
    SUBSCRIPTION_EVENT = "channel-subscribe-events-v1"
    # CHAT = "chat_moderator_actions.<user ID>.<channel ID>"
    # WHISPERS = "whispers.<user ID>"


class EventSub(WebSocket):
    EventMessages = Union[BitsBadgeEvent, BitsEvent, ChannelPointsEvent, SubscriptionEvent]
    EventCallable = Callable[[EventType, EventMessages], None]

    def __init__(self, broadcaster_id: str, service: Service) -> None:
        # super().__init__("ws://localhost:8080/eventsub", timeout=1)
        super().__init__("wss://eventsub-beta.wss.twitch.tv/ws", timeout=1)

        self.broadcaster_id = broadcaster_id
        self.service = service
        self.session_id: str | None = None
        self.has_started = False
        # self.last_ping_time: Optional[float] = None
        # self.nonce_waiting: MutableMapping[str, List[str]] = {}
        self.subscribers: List[EventSub.EventCallable] = []

    def start(self) -> None:
        self.connect()
        super().start()

    def connect(self) -> None:
        if not self.connected:
            gLogger.info("Starting EventSub connection...")
            self.has_started = False
            super().connect()
            # if self.connected:
            #     self.ping()
            #     self.listen(EventSubEventType.CHANNEL_POINTS_EVENT)
            #     self.listen(EventSubEventType.SUBSCRIPTION_EVENT)
            #     self.listen(EventSubEventType.BITS_EVENT)
            #     self.listen(EventSubEventType.BITS_BADGE_EVENT)

    def subscribe(self, subscriber: EventCallable):
        self.subscribers.append(subscriber)

    def create_subscription(self, name: str, condition: dict[str, Any], version: str = "1"):
        if self.session_id is None:
            return
        self.service.create_eventsub_subscription(name, version, condition, {
            "method": "websocket",
            "session_id": self.session_id
        })

    def handle_message(self, message: str):
        print(message)

        result = json.loads(message)

        metadata = result["metadata"]
        payload = result["payload"]

        if metadata["message_type"] == "session_welcome":
            gLogger.info("EventSub connection completed")
            self.session_id = payload["session"]["id"]
            self.has_started = True

            self.create_subscription("channel.channel_points_custom_reward_redemption.add",
                                     {"broadcaster_user_id": self.broadcaster_id})
            self.create_subscription("channel.subscribe", {"broadcaster_user_id": self.broadcaster_id})
            self.create_subscription("channel.subscription.gift", {"broadcaster_user_id": self.broadcaster_id})
            self.create_subscription("channel.subscription.message", {"broadcaster_user_id": self.broadcaster_id})
            self.create_subscription("channel.cheer", {"broadcaster_user_id": self.broadcaster_id})
            self.create_subscription("channel.raid", {"to_broadcaster_user_id": self.broadcaster_id})
        elif metadata["message_type"] == "session_keepalive":
            pass
        elif metadata["message_type"] == "notification":
            if payload["subscription"]["type"] == "channel.channel_points_custom_reward_redemption.add":
                channel_point_event = ChannelPointsEvent(**payload["event"])
                for sub in self.subscribers:
                    sub(EventType.REWARD_REDEEMED, channel_point_event)

        # if not self.has_started and result["type"] == "PONG":
        # if result["type"] == "RESPONSE":
        #     nonce = result["nonce"]
        #     if result["error"] != "":
        #         for listener in self.nonce_waiting[nonce]:
        #             gLogger.info("Error '" + result['error'] + "' when registering listener for: {}".format(listener))
        #     del self.nonce_waiting[nonce]
        # if result["type"] == "MESSAGE":
        #     data = result["data"]
        #     if data is not None and len(data) != 0:
        #         for sub in self.subscribers:
        #             data_topic = data["topic"]
        #             data_message = json.loads(data["message"])
        #             if data_topic.startswith(EventSubEventType.CHANNEL_POINTS_EVENT.value):
        #                 parsed_message = ChannelPointsEventMeta(**data_message)
        #                 sub(EventType.REWARD_REDEEMED, parsed_message.data)
        #             elif data_topic.startswith(EventSubEventType.BITS_EVENT.value):
        #                 parsed_message = BitsEventMeta(**data_message)
        #                 sub(EventType.BITS, parsed_message.data)
        #             elif data_topic.startswith(EventSubEventType.SUBSCRIPTION_EVENT.value):
        #                 parsed_message = SubscriptionEvent(**data_message)
        #                 sub(EventType.SUBSCRIPTION, parsed_message)
        #                 pass
        #             elif data_topic.startswith(EventSubEventType.BITS_BADGE_EVENT.value):
        #                 pass
        #             gLogger.info(f"PUB_SUB {data_topic} - {json.dumps(data_message)}")
