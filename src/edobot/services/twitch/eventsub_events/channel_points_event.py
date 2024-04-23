# import datetime
from typing import Any

# https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_reward_redemptionadd
class ChannelPointsEvent:
    class Reward:
        def __init__(self, **kwargs: Any) -> None:
            self.id: str = kwargs["id"]
            self.title: str = kwargs["title"]
            self.cost: int = kwargs["cost"]
            self.prompt: str = kwargs["prompt"]

    def __init__(self, **kwargs: Any) -> None:
        self.id : str = kwargs["id"]
        self.broadcaster_user_id : str = kwargs["broadcaster_user_id"]
        self.broadcaster_user_login : str = kwargs["broadcaster_user_login"]
        self.broadcaster_user_name : str = kwargs["broadcaster_user_name"]
        self.user_id : str = kwargs["user_id"]
        self.user_login : str = kwargs["user_login"]
        self.user_name : str = kwargs["user_name"]
        self.user_input : str = kwargs["user_input"]
        self.status : str = kwargs["status"]
        self.reward : ChannelPointsEvent.Reward = ChannelPointsEvent.Reward(**kwargs["reward"])
        self.redeemed_at : str = kwargs["id"]
