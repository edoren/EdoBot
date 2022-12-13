from typing import Any, List, Optional, Type, TypeVar

from .json_rpc_message import JSONRPCMessage

T = TypeVar("T", bound="SLOBSBase")


class SLOBSBase:

    def __init__(self, client, **kwargs: Any) -> None:
        self._client = client
        self.resourceId: str = kwargs["resourceId"]

    def _get_list(self, instance_type: Type[T], method: str, args: List[Any] = []) -> List[T]:
        scenes = self._call_method(method, args, False)
        return [instance_type(self._client, **x) for x in scenes]

    def _get_get_instance(self, instance_type: Type[T], method: str, args: List[Any] = []) -> T:
        result = self._call_method(method, args, False)
        return instance_type(self._client, **result)

    def _get_optional_instance(self, instance_type: Type[T], method: str, args: List[Any] = []) -> Optional[T]:
        result = self._call_method(method, args, True)
        return instance_type(self._client, **result) if result is not None else None

    def _call_method(self, method: str, args: List[Any] = [], optional: bool = True) -> Any:
        return self._client.send_and_wait_jsonrpc(JSONRPCMessage(method, {
            "resource": self.resourceId,
            "args": args
        }), optional)
