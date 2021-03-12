from enum import IntEnum
from typing import Optional

__all__ = ["Suscription", "SuscriptionTier"]


class SuscriptionTier(IntEnum):
    TIER_1 = 1000
    TIER_2 = 2000
    TIER_3 = 3000


class Suscription:
    def __init__(self,
                 broadcaster_id: str,
                 broadcaster_login: str,
                 broadcaster_name: str,
                 is_gift: bool,
                 tier: str,
                 plan_name: str,
                 user_id: str,
                 user_login: str,
                 user_name: str,
                 gifter_id: Optional[str] = None,
                 gifter_login: Optional[str] = None,
                 gifter_name: Optional[str] = None) -> None:
        self.broadcaster_id = broadcaster_id
        self.broadcaster_login = broadcaster_login
        self.broadcaster_name = broadcaster_name
        self.is_gift = is_gift
        self.tier = SuscriptionTier(int(tier))
        self.plan_name = plan_name
        self.user_id = user_id
        self.user_login = user_login
        self.user_name = user_name
        self.gifter_id = gifter_id
        self.gifter_login = gifter_login
        self.gifter_name = gifter_name
