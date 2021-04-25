import datetime
from typing import Any, Mapping, Optional

import dateutil.parser


class BitsEventMessage:
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
        self.time: str = kwargs["time"]
        self.total_bits_used: int = kwargs["total_bits_used"]
        self.badge_entitlement: Optional[Mapping[str, Any]] = kwargs.get("badge_entitlement", None)
        self.user_id: Optional[str] = kwargs.get("user_id", None)
        self.user_name: Optional[str] = kwargs.get("user_name", None)


class BitsEventMessageMeta:
    """[summary]

    Attributes:
        version (str):
            Message version
        message_id (str):
            Message ID.
        message_type (str):
            The type of object contained in the data field.
        data (BitsEventMessage):
            The data containing the
    """
    def __init__(self, **kwargs: Any):
        self.version: str = kwargs["version"]
        self.message_type: str = kwargs["message_type"]
        self.message_id: str = kwargs["message_id"]
        self.data: BitsEventMessage = BitsEventMessage(**kwargs["data"])


class BitsBadgeNotificationMessage:
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

    def __init__(self,
                 user_id: str,
                 user_name: str,
                 channel_id: str,
                 channel_name: str,
                 badge_tier: int,
                 time: str,
                 chat_message: Optional[str] = None) -> None:
        self.user_id = user_id
        self.user_name = user_name
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.badge_tier = badge_tier
        self.time = dateutil.parser.isoparse(time)
        self.chat_message = chat_message


class ChannelSubscriptionsEventMessage:
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
        message (Optional[str]):
            The body of the user-entered resub message. Depending on the type of message, the message body contains
            different fields
        sub_message (Optional[Mapping[str, Any]]):
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

    def __init__(self,
                 channel_id: str,
                 channel_name: str,
                 context: str,
                 sub_plan: str,
                 sub_plan_name: str,
                 time: str,
                 is_gift: bool,
                 user_id: Optional[str] = None,
                 user_name: Optional[str] = None,
                 display_name: Optional[str] = None,
                 message: Optional[str] = None,
                 sub_message: Optional[Mapping[str, Any]] = None,
                 recipient_id: Optional[str] = None,
                 recipient_user_name: Optional[str] = None,
                 recipient_display_name: Optional[str] = None,
                 cumulative_months: Optional[int] = None,
                 streak_months: Optional[int] = None,
                 multi_month_duration: Optional[int] = None) -> None:
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.context = context
        self.user_id = user_id
        self.user_name = user_name
        self.display_name = display_name
        self.message = message  # TODO: Check if really exist
        self.sub_message = sub_message  # TODO: Check not optional
        self.recipient_id = recipient_id
        self.recipient_user_name = recipient_user_name
        self.recipient_display_name = recipient_display_name
        self.sub_plan = sub_plan
        self.sub_plan_name = sub_plan_name
        self.time = dateutil.parser.isoparse(time)
        self.cumulative_months = cumulative_months
        self.streak_months = streak_months
        self.is_gift = is_gift
        self.multi_month_duration = multi_month_duration


class ChannelPointsEventMessage:
    """[summary]

    Attributes:
        timestamp (datetime.datetime):
            Time the pubsub message was sent
        redemption (ChannelPointsEventMessage.Redemption):
            Data about the redemption, includes unique id and user that redeemed it
    """

    class Redemption:
        """[summary]

        Attributes:
            channel_id (str):
                ID of the channel in which the reward was redeemed.
            redeemed_at (str):
                Timestamp in which a reward was redeemed
            user (Mapping[str, Any]):
                The user that redeem the reward
            reward (Mapping[str, Any]):
                Data about the reward that was redeemed
            status (str):
                Reward redemption status, will be FULFULLED if a user skips the reward queue, UNFULFILLED otherwise.
                Defaults to None.
            user_input (Optional[str], optional):
                A string that the user entered if the reward requires input
        """

        class Reward:
            class Image:
                def __init__(self, **kwargs: Any):
                    self.url_1x: str = kwargs["url_1x"]
                    self.url_2x: str = kwargs["url_2x"]
                    self.url_4x: str = kwargs["url_4x"]

            class MaxPerStream:
                def __init__(self, **kwargs: Any):
                    self.is_enabled: bool = kwargs["is_enabled"]
                    self.max_per_stream: int = kwargs["max_per_stream"]

            class MaxPerUserPerStream:
                def __init__(self, **kwargs: Any):
                    self.is_enabled: bool = kwargs["is_enabled"]
                    self.max_per_user_per_stream: int = kwargs["max_per_user_per_stream"]

            class GlobalCooldown:
                def __init__(self, **kwargs: Any):
                    self.is_enabled: bool = kwargs["is_enabled"]
                    self.global_cooldown_seconds: int = kwargs["global_cooldown_seconds"]

            def __init__(self, **kwargs: Any):
                self.id: str = kwargs["id"]
                self.channel_id: str = kwargs["channel_id"]
                self.title: str = kwargs["title"]
                self.prompt: str = kwargs["prompt"]
                self.cost: int = kwargs["cost"]
                self.is_user_input_required: bool = kwargs["is_user_input_required"]
                self.is_sub_only: bool = kwargs["is_sub_only"]
                self.image: Optional[__class__.Image] = __class__.Image(
                    **kwargs["image"]) if kwargs.get("image") else None
                self.default_image: __class__.Image = kwargs["default_image"]
                self.background_color: str = kwargs["background_color"]
                self.is_enabled: bool = kwargs["is_enabled"]
                self.is_paused: bool = kwargs["is_paused"]
                self.is_in_stock: bool = kwargs["is_in_stock"]
                self.max_per_stream: __class__.MaxPerStream = __class__.MaxPerStream(**kwargs["max_per_stream"])
                self.should_redemptions_skip_request_queue: bool = kwargs["should_redemptions_skip_request_queue"]
                self.template_id: Optional[str] = kwargs["template_id"]
                self.updated_for_indicator_at: datetime.datetime = dateutil.parser.isoparse(
                    kwargs["updated_for_indicator_at"])
                self.max_per_user_per_stream: __class__.MaxPerUserPerStream = __class__.MaxPerUserPerStream(
                    **kwargs["max_per_user_per_stream"])
                self.global_cooldown: __class__.GlobalCooldown = __class__.GlobalCooldown(**kwargs["global_cooldown"])
                self.redemptions_redeemed_current_stream: Optional[int] = kwargs["redemptions_redeemed_current_stream"]
                self.cooldown_expires_at: Optional[datetime.datetime] = dateutil.parser.isoparse(
                    kwargs["cooldown_expires_at"]) if kwargs.get("cooldown_expires_at") else None

        class User:
            def __init__(self, **kwargs: Any):
                self.id: str = kwargs["id"]
                self.login: str = kwargs["login"]
                self.display_name: str = kwargs["display_name"]

        def __init__(self, **kwargs: Any) -> None:
            self.id: str = kwargs["id"]
            self.channel_id: str = kwargs["channel_id"]
            self.redeemed_at: str = kwargs["redeemed_at"]
            self.user: __class__.User = __class__.User(**kwargs["user"])
            self.reward: __class__.Reward = __class__.Reward(**kwargs["reward"])
            self.status: str = kwargs["status"]
            self.user_input: Optional[str] = kwargs.get("user_input")

    def __init__(self, **kwargs: Any) -> None:
        self.timestamp: datetime.datetime = dateutil.parser.isoparse(kwargs["timestamp"])
        self.redemption = ChannelPointsEventMessage.Redemption(**kwargs["redemption"])


class ChannelPointsEventMessageMeta:
    def __init__(self, **kwargs: Any) -> None:
        self.type: str = kwargs["type"]
        self.data = ChannelPointsEventMessage(**kwargs["data"])
