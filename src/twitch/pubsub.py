import json
import logging
import random
import time
from enum import Enum
from typing import Callable, List, MutableMapping, Optional, Union

from model.pubsub_events import (BitsBadgeNotificationMessage, BitsEventMessage, ChannelPointsEventMessage,
                                 ChannelSubscriptionsEventMessage)
from network import WebSocket

__all__ = ["PubSub", "PubSubEvent"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class PubSubEvent(Enum):
    BITS = "channel-bits-events-v2"
    BITS_BADGE_NOTIFICATION = "channel-bits-badge-unlocks"
    CHANNEL_POINTS = "channel-points-channel-v1"
    CHANNEL_SUBSCRIPTIONS = "channel-subscribe-events-v1"
    # CHAT = "chat_moderator_actions.<user ID>.<channel ID>"
    # WHISPERS = "whispers.<user ID>"


class ChannelPointsEvent:
    pass


class PubSub(WebSocket):
    EventTypes = Union[BitsBadgeNotificationMessage,
                       BitsEventMessage, ChannelPointsEventMessage,
                       ChannelSubscriptionsEventMessage]
    EventCallable = Callable[[str, EventTypes], None]

    def __init__(self, broadcaster_id: str, password: str) -> None:
        super().__init__("wss://pubsub-edge.twitch.tv", timeout=1)

        self.broadcaster_id = broadcaster_id
        self.password = password
        self.last_ping_time: Optional[float] = None
        self.has_started = False
        self.nonce_waiting: MutableMapping[str, List[str]] = {}
        self.subscribers: List[PubSub.EventCallable] = []

    def start(self) -> None:
        self.connect()
        super().start()

    def connect(self) -> None:
        if not self.connected:
            gLogger.info("Starting PubSub connection...")
            self.has_started = False
            super().connect()
            if self.connected:
                self.ping()
                self.listen(PubSubEvent.CHANNEL_POINTS)
                self.listen(PubSubEvent.CHANNEL_SUBSCRIPTIONS)
                self.listen(PubSubEvent.BITS)
                self.listen(PubSubEvent.BITS_BADGE_NOTIFICATION)

    def subscribe(self, subscriber: EventCallable):
        self.subscribers.append(subscriber)

    def ping(self) -> None:
        # Send a PING message each 4:30 minutes
        current_time = time.time()
        if self.last_ping_time is None or (current_time - self.last_ping_time) >= 270:
            self.last_ping_time = current_time
            self.send('{"type":"PING"}')

    def listen(self, event: PubSubEvent):
        new_nonce = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        registered_topics = [f"{event.value}.{self.broadcaster_id}"]
        self.nonce_waiting[new_nonce] = registered_topics
        listen_request = {
            "type": "LISTEN",
            "nonce": new_nonce,
            "data": {
                "topics": registered_topics,
                "auth_token": self.password
            }
        }
        self.send(json.dumps(listen_request))

    def handle_message(self, message: str):
        result = json.loads(message)
        if not self.has_started and result["type"] == "PONG":
            gLogger.info("PubSub connection completed")
            self.has_started = True
        if result["type"] == "RESPONSE":
            nonce = result["nonce"]
            if result["error"] != "":
                for listener in self.nonce_waiting[nonce]:
                    gLogger.info("Error '" + result['error'] + "' when registering listener for: {}".format(listener))
            del self.nonce_waiting[nonce]
        if result["type"] == "MESSAGE":
            data = result["data"]
            if data is not None and len(data) != 0:
                for sub in self.subscribers:
                    data_topic = data["topic"]
                    data_message = json.loads(data["message"])
                    if data_topic.startswith(PubSubEvent.CHANNEL_POINTS.value):
                        # data_message["type"] # reward-redeemed
                        parsed_message = ChannelPointsEventMessage(**data_message["data"])  # TODO: data maybe missing
                        sub(data_topic, parsed_message)
                    gLogger.debug(f"PUB_SUB {data_topic} - {json.dumps(data_message)}")
