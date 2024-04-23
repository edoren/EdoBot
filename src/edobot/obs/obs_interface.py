import abc
from typing import Any, List, Mapping, Optional, Union

from .model import SceneModel


class OBSInterface(abc.ABC):
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    def set_config(self, config: Mapping[str, Any]):
        pass

    @abc.abstractmethod
    def is_connected(self) -> bool:
        pass

    @abc.abstractmethod
    def connect(self) -> None:
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        pass

    def get_scenes(self) -> List[SceneModel]:
        return []

    def get_current_scene(self) -> Optional[SceneModel]:
        pass

    def set_current_scene(self, scene: Union[SceneModel, str]) -> None:
        pass

    def set_text_gdi_plus_properties(self, source: str, **properties: Any) -> None:
        """
        Set the current properties of a Text GDI Plus source.

        :Arguments:
            *source*
                    type: String
                    Name of the source.
            *text*
                    type: String (optional)
                    Text content to be displayed.
        """
        pass
