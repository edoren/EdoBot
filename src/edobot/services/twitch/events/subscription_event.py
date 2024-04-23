import datetime
from typing import Any, List, Optional

import dateutil.parser


class SubscriptionEvent:
    """[summary]

    Attributes:
        channel_id (str):
            ID of the channel that has been subscribed or subgifted
        channel_name (str):
            Name of the channel that has been subscribed or subgifted
        context (str):
            Event type associated with the subscription product, values: sub, resub, subgift, anonsubgift, resubgift,
            anonresubgift
        user_id (Optional[str]):
            User ID of the person who subscribed or sent a gift subscription. None if anonymous
        user_name (Optional[str]):
            Login name of the person who subscribed or sent a gift subscription. None if anonymous
        display_name (Optional[str]):
            Display name of the person who subscribed or sent a gift subscription. None if anonymous
        sub_message (SubscriptionEvent.SubMessage):
            The body of the user-entered resub message. Depending on the type of message, the message body contains
            different fields
        recipient_id (Optional[str]):
            User ID of the subscription gift recipient
        recipient_user_name (Optional[str]):
            Login name of the subscription gift recipient
        recipient_display_name (Optional[str]):
            Display name of the person who received the subscription gift
        sub_plan (str):
            Subscription Plan ID, values: Prime, 1000, 2000, 3000
        sub_plan_name (str):
            Channel Specific Subscription Plan Name
        time (datetime.datetime):
            Time when the subscription or gift was completed.
        cumulative_months (Optional[int]):
            Cumulative number of tenure months of the subscription
        streak_months (Optional[int]):
            Denotes the user’s most recent (and contiguous) subscription tenure streak in the channel
        is_gift (bool):
            If this sub message was caused by a gift subscription
        multi_month_duration (Optional[int]):
            Number of months gifted as part of a single, multi-month gift OR number of months purchased as part of a
            multi-month subscription
    """

    class Emote:

        def __init__(self, **kwargs: Any):
            self.start: str = kwargs["start"]
            self.end: str = kwargs["end"]
            self.id: str = kwargs["id"]

    class SubMessage:

        def __init__(self, **kwargs: Any):
            self.message: str = kwargs["message"]
            if kwargs.get("emotes") is not None:
                self.emotes: Optional[List[SubscriptionEvent.Emote]] = [
                    SubscriptionEvent.Emote(**x) for x in kwargs["emotes"]
                ]
            else:
                self.emotes: Optional[List[SubscriptionEvent.Emote]] = None

    def __init__(self, **kwargs: Any) -> None:
        self.channel_id: str = kwargs["channel_id"]
        self.channel_name: str = kwargs["channel_name"]
        self.context: str = kwargs["context"]
        self.user_id: Optional[str] = kwargs.get("user_id")
        self.user_name: Optional[str] = kwargs.get("user_name")
        self.display_name: Optional[str] = kwargs.get("display_name")
        self.sub_message: Optional[SubscriptionEvent.SubMessage] = SubscriptionEvent.SubMessage(
            **kwargs["sub_message"]) if kwargs.get("sub_message") else None
        self.recipient_id: Optional[str] = kwargs.get("recipient_id")
        self.recipient_user_name: Optional[str] = kwargs.get("recipient_user_name")
        self.recipient_display_name: Optional[str] = kwargs.get("recipient_display_name")
        self.sub_plan: str = kwargs["sub_plan"]
        self.sub_plan_name: str = kwargs["sub_plan_name"]
        self.time: datetime.datetime = dateutil.parser.isoparse(kwargs["time"])
        self.cumulative_months: Optional[int] = kwargs.get("cumulative_months")
        self.streak_months: Optional[int] = kwargs.get("streak_months")
        self.is_gift: bool = kwargs["is_gift"]
        self.multi_month_duration: Optional[int] = kwargs.get("multi_month_duration")
