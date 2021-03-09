import abc

from config import Config


class TwitchChatComponent:
    def __init__(self, config: Config):
        pass

    @abc.abstractmethod
    def get_name(self) -> str:
        pass
