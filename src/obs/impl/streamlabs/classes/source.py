from typing import Any, List, Mapping

from ..base.slobs_base import SLOBSBase


class Source(SLOBSBase):
    def __init__(self, client, **kwargs: Any) -> None:
        super().__init__(client, **kwargs)
        self.name = kwargs["name"]

    def setPropertiesFormData(self, properties: List[Mapping[str, Any]]):
        self._call_method("setPropertiesFormData", [properties])
