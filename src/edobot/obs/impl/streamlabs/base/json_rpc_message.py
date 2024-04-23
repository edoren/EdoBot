import json
import threading
from typing import Any, Mapping


class JSONRPCMessage:
    counter = 1
    counter_lock = threading.Lock()

    def __init__(self, method: str, params: Any) -> None:
        with JSONRPCMessage.counter_lock:
            self.payload: Mapping[str, Any] = {
                "jsonrpc": "2.0",
                "id": JSONRPCMessage.counter,
                "method": method,
                "params": params,
            }
            JSONRPCMessage.counter += 1

    def get_id(self) -> int:
        return self.payload["id"]

    def json(self) -> str:
        return json.dumps(self.payload)

    def __str__(self) -> str:
        return self.json()
