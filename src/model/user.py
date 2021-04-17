__all__ = ["User"]


from typing import Any, Optional


class User:
    def __init__(self, **kwargs: Any) -> None:
        self.broadcaster_type: str = kwargs["broadcaster_type"]
        self.description: str = kwargs["description"]
        self.display_name: str = kwargs["display_name"]
        self.id: str = kwargs["id"]
        self.login: str = kwargs["login"]
        self.offline_image_url: str = kwargs["offline_image_url"]
        self.profile_image_url: str = kwargs["profile_image_url"]
        self.type: str = kwargs["type"]
        self.view_count: int = kwargs["view_count"]
        self.created_at: str = kwargs["created_at"]
        self.email: Optional[str] = kwargs.get("email", None)
