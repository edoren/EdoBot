import uuid
from typing import Any, List, Mapping, MutableMapping

from model.event_type import EventType


class RewardTimer:

    class Event:

        def __init__(self, **kwargs: Any):
            alt_type = kwargs["type"]
            if isinstance(alt_type, EventType):
                self.type = alt_type
            else:
                if alt_type == "reward":
                    self.type = EventType.REWARD_REDEEMED
                elif alt_type == "subscription":
                    self.type = EventType.SUBSCRIPTION
                elif alt_type == "bits":
                    self.type = EventType.BITS
            self.id: str = kwargs.get("id", uuid.uuid4().hex)
            self.enabled: bool = kwargs.get("enabled", True)
            self.duration: int = kwargs.get("duration", 30)
            self.duration_format: str = kwargs.get("duration_format", "seconds")
            if "data" in kwargs:
                self.data: MutableMapping[str, Any] = kwargs["data"]
            elif self.type == EventType.REWARD_REDEEMED:
                self.data: MutableMapping[str, Any] = {"name": ""}
            elif self.type == EventType.SUBSCRIPTION:
                self.data: MutableMapping[str, Any] = {"is_gift": False, "type": "prime"}
            elif self.type == EventType.BITS:
                self.data: MutableMapping[str, Any] = {"is_exact": False, "num_bits": 100}
            else:
                self.data: MutableMapping[str, Any] = {}

        def serialize(self) -> Mapping[str, Any]:
            if self.type == EventType.REWARD_REDEEMED:
                type_name = "reward"
            elif self.type == EventType.SUBSCRIPTION:
                type_name = "subscription"
            elif self.type == EventType.BITS:
                type_name = "bits"
            else:
                type_name = "unknown"
            return {
                "id": self.id,
                "type": type_name,
                "enabled": self.enabled,
                "duration": self.duration,
                "duration_format": self.duration_format,
                "data": self.data
            }

        def get_duration_ms(self) -> int:
            if self.duration_format == "hours":
                return self.duration * 3600000
            elif self.duration_format == "minutes":
                return self.duration * 60000
            elif self.duration_format == "seconds":
                return self.duration * 1000
            else:
                return 0

    def __init__(self, name: str, **kwargs: Any):
        self.id: str = kwargs.get("id", uuid.uuid4().hex)
        self.name: str = name
        self.enabled: bool = kwargs.get("enabled", True)
        self.display: str = kwargs.get("display", "minutes")
        self.format: str = kwargs.get("format", "{name}: {time}")
        self.display: str = kwargs.get("display", "minutes")
        self.source: str = kwargs.get("source", "")
        self.start_msg: str = kwargs.get("start_msg", "")
        self.finish_msg: str = kwargs.get("finish_msg", "")
        self.events: List[RewardTimer.Event] = [RewardTimer.Event(**x) for x in kwargs.get("events", [])]

    def __hash__(self):
        return hash((self.id, self.name))

    def __eq__(self, other: "RewardTimer"):
        return (self.id, self.name) == (other.id, other.name)

    def __ne__(self, other: "RewardTimer"):
        return not (self == other)

    def has_event(self, etype: EventType, **kwargs: Any) -> bool:
        return len(self.get_events(etype, **kwargs)) != 0

    def get_events(self, etype: EventType, **kwargs: Any) -> List["RewardTimer.Event"]:
        events = []
        for event in self.events:
            if event.type == etype:
                if kwargs:
                    if etype == EventType.REWARD_REDEEMED:
                        if kwargs["name"] == event.data["name"]:
                            events.append(event)
                    elif etype == EventType.SUBSCRIPTION:
                        ok = kwargs["is_gift"] == event.data["is_gift"]
                        ok = ok and (kwargs["type"] == event.data["type"] or event.data["type"] == "any")
                        if ok:
                            events.append(event)
                else:
                    events.append(event)
        return events

    def serialize(self) -> Mapping[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "display": self.display,
            "format": self.format,
            "source": self.source,
            "start_msg": self.start_msg,
            "finish_msg": self.finish_msg,
            "events": [x.serialize() for x in self.events]
        }
