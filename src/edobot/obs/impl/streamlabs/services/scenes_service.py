from typing import List, Optional

from ..base.slobs_base import SLOBSBase
from ..classes.scene import Scene


class ScenesService(SLOBSBase):
    def __init__(self, client) -> None:
        super().__init__(client, resourceId="ScenesService")

        # Observers
        # self.itemAdded = Signal(ISceneItemModel)
        # self.itemRemoved = Signal(ISceneItemModel)
        # self.itemUpdated = Signal(ISceneItemModel)
        # self.sceneAdded = Signal(ISceneModel)
        # self.sceneRemoved = Signal(ISceneModel)
        # self.sceneSwitched = Signal(ISceneModel)

    def activeScene(self) -> Scene:
        return self._get_get_instance(Scene, "activeScene")

    def activeSceneId(self) -> str:
        return self._call_method("activeSceneId")

    # Methods
    def createScene(self, name: str):
        return self._get_optional_instance(Scene, "createScene", [name])

    def getScene(self, scene_id: str) -> Optional[Scene]:
        return self._get_optional_instance(Scene, "getScene", [scene_id])

    def getScenes(self) -> List[Scene]:
        return self._get_list(Scene, "getScenes")

    def makeSceneActive(self, scene_id: str) -> bool:
        return self._call_method("makeSceneActive", [scene_id])

    def removeScene(self, scene_id: str):
        self._call_method("removeScene", [scene_id])
