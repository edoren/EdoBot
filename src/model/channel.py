__all__ = ["Channel"]

from typing import Any


class Channel:
    def __init__(self, **kwargs: Any) -> None:
        self.broadcaster_id: str = kwargs["broadcaster_id"]
        self.broadcaster_name: str = kwargs["broadcaster_name"]
        self.game_name: str = kwargs["game_name"]
        self.game_id: str = kwargs["game_id"]
        self.broadcaster_language: str = kwargs["broadcaster_language"]
        self.title: str = kwargs["title"]
        self.delay: int = kwargs["delay"]
