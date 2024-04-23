from typing import Any, Optional

from .scene_node import SceneNode
from .source import Source


class SceneItem(SceneNode):

    def __init__(self, client, **kwargs: Any) -> None:
        super().__init__(client, **kwargs)

    def getSource(self) -> Optional[Source]:
        return self._get_optional_instance(Source, "getSource")
