from typing import Any


class SceneModel:

    def __init__(self, **kwargs: Any) -> None:
        self.name: str = kwargs["name"]
