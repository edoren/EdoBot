import logging
import time
from typing import List, MutableMapping, Optional

import model
from core.constants import Constants
from model.access_token import AccessToken
from network.cache_request import CacheRequest

__all__ = ["Service"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class UnauthenticatedException(Exception):
    pass


class Service:
    def __init__(self, token: AccessToken):
        self.token = token

        self.__active = True

        self.users_cache: MutableMapping[str, CacheRequest] = {}

        user = self.get_user()
        if user is not None:
            self.user: model.User = user

        self.mod_requestor = self.__get_cache_requestor("GET", "/moderation/moderators",
                                                        params={"broadcaster_id": self.user.id})
        self.sub_requestor = self.__get_cache_requestor("GET", "/subscriptions",
                                                        params={"broadcaster_id": self.user.id})

    def __call_endpoint(self, requestor: CacheRequest):
        retry_time = 1
        while self.__active:
            try:
                request = requestor.call(False)
                if request.status_code == 200:
                    return request.json()
                elif request.status_code == 401:
                    raise UnauthenticatedException("Unauthenticated: Missing/invalid Token")
                else:
                    gLogger.error(f"Error reaching url '{request.url}' failed: {request.json()}")
                    return {"data": None}
            except UnauthenticatedException as e:
                raise e
            except Exception as e:
                gLogger.error(f"Error reaching url '{requestor.url}' retying in {retry_time} seconds: {e}")
                time.sleep(retry_time)
                retry_time *= 2
                continue
        return {"data": None}

    def get_moderators(self) -> List[model.Moderator]:
        response = self.__call_endpoint(self.mod_requestor)
        return [model.Moderator(**x) for x in response["data"] or []]

    def get_subscribers(self) -> List[model.Suscription]:
        response = self.__call_endpoint(self.sub_requestor)
        return [model.Suscription(**x) for x in response["data"] or []]

    def get_user(self, name: Optional[str] = None) -> Optional[model.User]:
        if name is None:
            name = "$"
            requestor = self.users_cache.setdefault(name, self.__get_cache_requestor("GET", "/users"))
        else:
            requestor = self.users_cache.setdefault(name, self.__get_cache_requestor("GET", "/users",
                                                                                     params={"login": name}))
        response = self.__call_endpoint(requestor)
        users = [model.User(**x) for x in response["data"] or []]
        user = None if len(users) == 0 else users[0]
        if user and name == "$":
            self.users_cache[user.login] = self.users_cache["$"]
        return user

    def __get_cache_requestor(self, method, path, params=None):
        return CacheRequest(method, "https://api.twitch.tv/helix" + path, params=params, headers={
            "Authorization": f"{self.token.token_type.title()} {self.token.access_token}",
            "Client-Id": Constants.CLIENT_ID
        })

    def __del__(self):
        self.__active = False
