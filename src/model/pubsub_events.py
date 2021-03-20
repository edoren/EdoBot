from typing import Any, Mapping, Optional

import dateutil.parser


class BitsEventMessage:
    """[summary]

    Attributes:
        bits_used (int):
            Number of Bits used.
        channel_id (str):
            ID of the channel in which Bits were used.
        chat_message (str):
            Chat message sent with the cheer.
        context (str):
            Event type associated with this use of Bits.
        is_anonymous (bool):
            Whether or not the event was anonymous.
        message_id (str):
            Message ID.
        message_type (str):
            The type of object contained in the data field.
        time (datetime.datetime):
            Time when the Bits were used.
        total_bits_used (int):
            All time total number of Bits used in the channel by a specified user.
        version (str):
            Message version
        badge_entitlement (Optional[Mapping[str, Any]]):
            Information about a user’s new badge level, if the cheer was not anonymous and the user reached a new badge
            level with this cheer. Otherwise, null.
        user_id (Optional[str]):
            User ID of the person who used the Bits - if the cheer was not anonymous. None if anonymous.
        user_name (Optional[str]):
            Login name of the person who used the Bits - if the cheer was not anonymous. None if anonymous
    """

    def __init__(self,
                 bits_used: int,
                 channel_id: str,
                 chat_message: str,
                 context: str,
                 is_anonymous: bool,
                 message_id: str,
                 message_type: str,
                 time: str,
                 total_bits_used: int,
                 version: str,
                 badge_entitlement: Optional[Mapping[str, Any]] = None,
                 user_id: Optional[str] = None,
                 user_name: Optional[str] = None) -> None:
        self.badge_entitlement = badge_entitlement
        self.bits_used = bits_used
        self.channel_id = channel_id
        self.chat_message = chat_message
        self.context = context
        self.is_anonymous = is_anonymous
        self.message_id = message_id
        self.message_type = message_type
        self.time = dateutil.parser.isoparse(time)
        self.total_bits_used = total_bits_used
        self.user_id = user_id
        self.user_name = user_name
        self.version = version


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

        def __init__(self,
                     id: str,
                     channel_id: str,
                     redeemed_at: str,
                     user: Mapping[str, Any],
                     reward: Mapping[str, Any],
                     status: str,
                     user_input: Optional[str] = None) -> None:
            self.id = id
            self.channel_id = channel_id
            self.redeemed_at = redeemed_at
            self.user = user
            self.reward = reward
            self.user_input = user_input
            self.status = status

    def __init__(self,
                 timestamp: str,
                 redemption: Mapping[str, Any]) -> None:
        self.timestamp = dateutil.parser.isoparse(timestamp)
        self.redemption = ChannelPointsEventMessage.Redemption(**redemption)
