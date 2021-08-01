import datetime
from typing import Any, Optional

import dateutil.parser


class BitsBadgeEvent:
    """[summary]

    Attributes:
        user_id (str):
            ID of user who earned the new Bits badge.
        user_name (str):
            Login of user who earned the new Bits badge.
        channel_id (str):
            ID of channel where user earned the new Bits badge.
        channel_name (str):
            Login of channel where user earned the new Bits badge.
        badge_tier (int):
            Value of Bits badge tier that was earned (1000, 10000, etc.)
        chat_message (Optional[str]):
            Custom message included with share. Defaults to None.
        time (str):
            Time when the new Bits badge was earned.
    """
    def __init__(self, **kwargs: Any) -> None:
        self.user_id: str = kwargs["user_id"]
        self.user_name: str = kwargs["user_name"]
        self.channel_id: str = kwargs["channel_id"]
        self.channel_name: str = kwargs["channel_name"]
        self.badge_tier: str = kwargs["badge_tier"]
        self.time: datetime.datetime = dateutil.parser.isoparse(kwargs["time"])
        self.chat_message: Optional[str] = kwargs.get("chat_message")
