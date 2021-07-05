from enum import IntEnum

__all__ = ["UserType"]


class UserType(IntEnum):
    BROADCASTER = 1
    EDITOR = 2
    MODERATOR = 3
    VIP = 4
    SUBSCRIPTOR = 5
    CHATTER = 6
