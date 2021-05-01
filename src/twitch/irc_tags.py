from typing import Any, Optional


class PrivateMsgTags:
    def __init__(self, badge_info: str, badges: str, color: str, display_name: str, emotes: str, flags: str, id: str,
                 mod: str, room_id: str, tmi_sent_ts: str, user_id: str, bits: Optional[str] = None,
                 client_nonce: Optional[str] = None, emote_only: Optional[str] = None,
                 custom_reward_id: Optional[str] = None, msg_id: Optional[str] = None,
                 reply_parent_display_name: Optional[str] = None, reply_parent_msg_body: Optional[str] = None,
                 reply_parent_msg_id: Optional[str] = None, reply_parent_user_id: Optional[str] = None,
                 reply_parent_user_login: Optional[str] = None, **kwargs: Any) -> None:
        self.sub_months = 0
        if badge_info:
            self.sub_months = int(badge_info.split("/")[-1])
        self.badges = {}
        if badges:
            for badge_data in badges.split(","):
                badge, value = badge_data.split("/")
                self.badges[badge] = value
        self.color = color
        self.display_name = display_name
        self.emotes = {}
        if emotes:
            for emote_data in emotes.split("/"):
                emote_id, indexes = emote_data.split(":")
                index_list = []
                for index in indexes.split(","):
                    first, last = index.split("-")
                    index_list.append((int(first), int(last)))
                self.emotes[emote_id] = index_list
        self.flags = flags
        self.id = id
        self.mod = (mod == "1")
        self.room_id = room_id
        self.tmi_sent_ts = tmi_sent_ts
        self.user_id = user_id
        self.bits = bits
        self.client_nonce = client_nonce
        self.emote_only = emote_only
        self.custom_reward_id = custom_reward_id
        self.msg_id = msg_id
        self.reply_parent_display_name = reply_parent_display_name
        self.reply_parent_msg_body = reply_parent_msg_body
        self.reply_parent_msg_id = reply_parent_msg_id
        self.reply_parent_user_id = reply_parent_user_id
        self.reply_parent_user_login = reply_parent_user_login
        if __debug__ and kwargs:
            print("Missing args: ", kwargs)
