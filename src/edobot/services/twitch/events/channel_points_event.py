import datetime
from typing import Any, Optional

import dateutil.parser


class ChannelPointsEvent:
    """[summary]

    Attributes:
        timestamp (datetime.datetime):
            Time the pubsub message was sent
        redemption (ChannelPointsEvent.Redemption):
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
                self.image: Optional[__class__.Image] = (
                    __class__.Image(**kwargs["image"]) if kwargs.get("image") else None
                )
                self.default_image: __class__.Image = kwargs["default_image"]
                self.background_color: str = kwargs["background_color"]
                self.is_enabled: bool = kwargs["is_enabled"]
                self.is_paused: bool = kwargs["is_paused"]
                self.is_in_stock: bool = kwargs["is_in_stock"]
                self.max_per_stream: __class__.MaxPerStream = __class__.MaxPerStream(**kwargs["max_per_stream"])
                self.should_redemptions_skip_request_queue: bool = kwargs["should_redemptions_skip_request_queue"]
                self.template_id: Optional[str] = kwargs["template_id"]
                self.updated_for_indicator_at: datetime.datetime = dateutil.parser.isoparse(
                    kwargs["updated_for_indicator_at"]
                )
                self.max_per_user_per_stream: __class__.MaxPerUserPerStream = __class__.MaxPerUserPerStream(
                    **kwargs["max_per_user_per_stream"]
                )
                self.global_cooldown: __class__.GlobalCooldown = __class__.GlobalCooldown(**kwargs["global_cooldown"])
                self.redemptions_redeemed_current_stream: Optional[int] = kwargs["redemptions_redeemed_current_stream"]
                self.cooldown_expires_at: Optional[datetime.datetime] = (
                    dateutil.parser.isoparse(kwargs["cooldown_expires_at"])
                    if kwargs.get("cooldown_expires_at")
                    else None
                )

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
        self.redemption = ChannelPointsEvent.Redemption(**kwargs["redemption"])


class ChannelPointsEventMeta:
    def __init__(self, **kwargs: Any) -> None:
        self.type: str = kwargs["type"]
        self.data = ChannelPointsEvent(**kwargs["data"])
