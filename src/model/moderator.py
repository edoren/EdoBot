__all__ = ["Moderator"]


class Moderator:
    def __init__(self, user_id: str, user_login: str, user_name: str) -> None:
        self.user_id = user_id
        self.user_login = user_login
        self.user_name = user_name
