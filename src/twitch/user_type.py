from enum import IntEnum

__all__ = ["UserType"]


class UserType(IntEnum):
    BROADCASTER = 1
    MODERATOR = 2
    VIP = 3  # NOT WORKING
    SUBSCRIPTOR = 4
    CHATTER = 5
