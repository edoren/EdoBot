__all__ = ["User"]


from typing import Optional


class User:
    def __init__(self, broadcaster_type: str,
                 description: str,
                 display_name: str,
                 id: str,
                 login: str,
                 offline_image_url: str,
                 profile_image_url: str,
                 type: str,
                 view_count: int,
                 created_at: str,
                 email: Optional[str] = None) -> None:
        self.broadcaster_type = broadcaster_type
        self.description = description
        self.display_name = display_name
        self.id = id
        self.login = login
        self.offline_image_url = offline_image_url
        self.profile_image_url = profile_image_url
        self.type = type
        self.view_count = view_count
        self.email = email
        self.created_at = created_at
