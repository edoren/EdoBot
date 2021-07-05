from enum import IntEnum

__all__ = ["EventType"]


class EventType(IntEnum):
    REWARD_REDEEMED = 1
    BITS = 2
    RAID = 3
