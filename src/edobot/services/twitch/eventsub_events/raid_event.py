from typing import Any


class RaidEvent:
    """[summary]

    Attributes:
        display_name (str):
            Name of the channel that raided
        login (str):
            The login name of the channel that raided
        profile_image_url (str):
            The image url of the channel that raided
        viewer_count (int):
            The amount of viewers that came with the raid
    """

    def __init__(self, **kwargs: Any) -> None:
        self.display_name = kwargs["msg_param_displayName"]
        self.login = kwargs["msg_param_login"]
        self.profile_image_url = kwargs["msg_param_profileImageURL"]
        self.viewer_count = int(kwargs.get("msg_param_viewerCount", 0))
