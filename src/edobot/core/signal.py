import threading
from typing import Any, Callable, Set


class Signal:

    def __init__(self, *types: type) -> None:
        self.types = list(types)
        self.connection_id = 0
        self.connections: Set[Callable[..., None]] = set()
        self._lock = threading.Lock()

    def connect(self, callback: Callable[..., None]):
        with self._lock:
            self.connections.add(callback)

    def disconnect(self, callback: Callable[..., None]):
        with self._lock:
            self.connections.remove(callback)

    def emit(self, *args: Any):
        if len(args) != len(self.types):
            return
        if __debug__:
            args_types = [type(x) for x in args]
            if args_types != self.types:
                print(f"Calling with wrong types {args_types} expected {self.types}")
                return
        with self._lock:
            for callback in self.connections:
                callback(*args)
