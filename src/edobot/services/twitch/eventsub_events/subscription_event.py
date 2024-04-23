from typing import Any


class Emotes:

    def __init__(self, **kwargs: Any) -> None:
        self.id: str = kwargs.get("id", "")
        self.begin: int = kwargs.get("begin", 0)
        self.end: int = kwargs.get("end", 0)


class SubscriptionEvent:

    class Message:

        def __init__(self, **kwargs: Any) -> None:
            self.text: str = kwargs["text"]
            if "emotes" in kwargs:
                self.emotes: list[Emotes] = [Emotes(**e) for e in kwargs["emotes"]]

    def __init__(self, **kwargs: Any) -> None:
        self.user_id: str = kwargs.get("user_id", "")
        self.user_login: str = kwargs.get("user_login", "")
        self.user_name: str = kwargs.get("user_name", "")
        self.broadcaster_user_id: str = kwargs.get("broadcaster_user_id", "")
        self.broadcaster_user_login: str = kwargs.get("broadcaster_user_login", "")
        self.broadcaster_user_name: str = kwargs.get("broadcaster_user_name", "")

        self.tier: str = kwargs.get("tier", "1000")
        self.is_gift: bool = kwargs.get("is_gift", False)

        self.total: int = kwargs.get("total", 1)
        # self.tier: str = kwargs.get("tier", "1000")
        self.cumulative_total: int | None = kwargs.get("cumulative_total", None)
        self.is_anonymous: bool = kwargs.get("is_anonymous", False)

        self.message: SubscriptionEvent.Message | None = None
        if "message" in kwargs:
            self.message = SubscriptionEvent.Message(**kwargs["message"])
        self.cumulative_months: int = kwargs.get("cumulative_months", 1)
        self.streak_months: int | None = kwargs.get("streak_months", 1)
        self.duration_months: int = kwargs.get("duration_months", 0)
