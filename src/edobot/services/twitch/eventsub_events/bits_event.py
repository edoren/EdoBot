import datetime
from typing import Any, Mapping, Optional

import dateutil.parser


class BitsEvent:
    """[summary]

    Attributes:
        bits_used (int):
            Number of Bits used.
        channel_id (str):
            ID of the channel in which Bits were used.
        channel_name (str):
            Name of the channel in which Bits were used.
        chat_message (str):
            Chat message sent with the cheer.
        context (str):
            Event type associated with this use of Bits.
        is_anonymous (bool):
            Whether or not the event was anonymous.
        time (datetime.datetime):
            Time when the Bits were used.
        total_bits_used (int):
            All time total number of Bits used in the channel by a specified user.
        badge_entitlement (Optional[Mapping[str, Any]]):
            Information about a user’s new badge level, if the cheer was not anonymous and the user reached a new badge
            level with this cheer. Otherwise, null.
        user_id (Optional[str]):
            User ID of the person who used the Bits - if the cheer was not anonymous. None if anonymous.
        user_name (Optional[str]):
            Login name of the person who used the Bits - if the cheer was not anonymous. None if anonymous
    """

    def __init__(self, **kwargs: Any) -> None:
        self.bits_used: int = kwargs["bits_used"]
        self.channel_id: str = kwargs["channel_id"]
        self.channel_name: Optional[str] = kwargs.get("channel_name", None)  # Optional?
        self.chat_message: str = kwargs["chat_message"]
        self.context: str = kwargs["context"]
        self.is_anonymous: bool = kwargs["is_anonymous"]
        self.time: datetime.datetime = dateutil.parser.isoparse(kwargs["time"])
        self.total_bits_used: int = kwargs["total_bits_used"]
        self.badge_entitlement: Optional[Mapping[str, Any]] = kwargs.get("badge_entitlement", None)
        self.user_id: Optional[str] = kwargs.get("user_id", None)
        self.user_name: Optional[str] = kwargs.get("user_name", None)


class BitsEventMeta:
    """[summary]

    Attributes:
        version (str):
            Message version
        message_id (str):
            Message ID.
        message_type (str):
            The type of object contained in the data field.
        data (BitsEvent):
            The data containing the
    """

    def __init__(self, **kwargs: Any):
        self.version: str = kwargs["version"]
        self.message_type: str = kwargs["message_type"]
        self.message_id: str = kwargs["message_id"]
        self.data: BitsEvent = BitsEvent(**kwargs["data"])
