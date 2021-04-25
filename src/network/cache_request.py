import time
from typing import Any, Optional

import requests


class CacheRequest:
    def __init__(self, method: str, url: str, timeout_seconds: int = 5 * 60, **kwargs: Any):
        self.method = method
        self.url = url
        self.timeout = timeout_seconds * 1000
        self.expire_time: Optional[int] = None
        self.cached_response: Optional[requests.Response] = None
        self.request_kargs = kwargs
        if method == "GET":
            self.request_kargs.setdefault('allow_redirects', True)
        self.request_kargs.setdefault("params", None)

    def set_timeout(self, timeout_seconds: int):
        self.timeout = timeout_seconds * 1000

    def call(self, force: bool = False) -> requests.Response:
        current_time = round(time.time() * 1000)
        if force or self.expire_time is None or self.cached_response is None or current_time > self.expire_time:
            self.expire_time = current_time + self.timeout
            self.cached_response = requests.request(self.method, self.url, **self.request_kargs)
            return self.cached_response
        else:
            return self.cached_response
