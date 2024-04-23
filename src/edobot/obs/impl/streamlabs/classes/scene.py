from typing import Any, List, Optional

from ..base.slobs_base import SLOBSBase
from .scene_item import SceneItem


class Scene(SLOBSBase):
    def __init__(self, client, **kwargs: Any) -> None:
        super().__init__(client, **kwargs)
        self.id: str = kwargs["id"]
        self.name: str = kwargs["name"]
        self.nodes: List[Any] = kwargs["nodes"]

    def getNodeByName(self, name: str) -> Optional[SceneItem]:
        return self._get_optional_instance(SceneItem, "getNodeByName", [name])
