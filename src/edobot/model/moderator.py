__all__ = ["Moderator"]

from typing import Any


class Moderator:
    def __init__(self, **kwargs: Any) -> None:
        self.user_id: str = kwargs["user_id"]
        self.user_login: str = kwargs["user_login"]
        self.user_name: str = kwargs["user_name"]
