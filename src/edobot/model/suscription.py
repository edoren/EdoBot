from enum import IntEnum
from typing import Any, Optional

__all__ = ["Suscription", "SuscriptionTier"]


class SuscriptionTier(IntEnum):
    TIER_1 = 1000
    TIER_2 = 2000
    TIER_3 = 3000


class Suscription:

    def __init__(self, **kwargs: Any) -> None:
        self.broadcaster_id: str = kwargs["broadcaster_id"]
        self.broadcaster_login: str = kwargs["broadcaster_login"]
        self.broadcaster_name: str = kwargs["broadcaster_name"]
        self.is_gift: bool = kwargs["is_gift"]
        self.tier: int = SuscriptionTier(int(kwargs["tier"]))
        self.plan_name: str = kwargs["plan_name"]
        self.user_id: str = kwargs["user_id"]
        self.user_login: str = kwargs["user_login"]
        self.user_name: str = kwargs["user_name"]
        self.gifter_id: Optional[str] = kwargs.get("gifter_id", None)
        self.gifter_login: Optional[str] = kwargs.get("gifter_login", None)
        self.gifter_name: Optional[str] = kwargs.get("gifter_name", None)
