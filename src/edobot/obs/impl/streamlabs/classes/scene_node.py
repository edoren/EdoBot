from typing import Any, Optional

from ..base.slobs_base import SLOBSBase


class SceneNode(SLOBSBase):
    def __init__(self, client, **kwargs: Any) -> None:
        super().__init__(client, **kwargs)
        self.id: str = kwargs["id"]
        self.nodeId: Optional[str] = kwargs.get("nodeId", None)
        self.parentId: str = kwargs["parentId"]
        self.sceneId: str = kwargs["sceneId"]
        self.sceneNodeType: str = kwargs["sceneNodeType"]
