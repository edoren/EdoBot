from typing import List

__all__ = ["AccessToken"]


class AccessToken:
    def __init__(self, access_token: str,
                 scope: List[str], token_type: str,
                 state=[]) -> None:
        self.access_token = access_token
        self.scope = scope
        self.token_type = token_type
        self.state = state

    def __str__(self):
        return f"{self.token_type.title()} {self.access_token}"
