from typing import Any, List

__all__ = ["AccessToken"]


class AccessToken:
    def __init__(self, **kwargs: Any) -> None:
        self.access_token: str = kwargs["access_token"]
        self.scope: List[str] = kwargs["scope"]
        self.token_type: str = kwargs["token_type"]
        self.state: List[Any] = kwargs["state"]

    def __str__(self):
        return f"{self.token_type.title()} {self.access_token}"
