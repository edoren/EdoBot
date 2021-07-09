import logging
import time
from typing import List, MutableMapping, Optional, overload

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
        self.channel_cache: MutableMapping[str, CacheRequest] = {}
        self.channel_editors_cache: Optional[CacheRequest] = None

        self.mod_requestor: Optional[CacheRequest] = None
        self.sub_requestor: Optional[CacheRequest] = None

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
                last_try_time = time.time()
                while self.__active and time.time() < (last_try_time + retry_time):
                    time.sleep(1)
                retry_time *= 2
                continue
        return {"data": None}

    def get_moderators(self) -> List[model.Moderator]:
        if self.mod_requestor is None:
            user = self.get_user()
            self.mod_requestor = self.__get_cache_requestor("GET", "/moderation/moderators",
                                                            params={"broadcaster_id": user.id})
        response = self.__call_endpoint(self.mod_requestor)
        return [model.Moderator(**x) for x in response["data"] or []]

    def get_subscribers(self) -> List[model.Suscription]:
        if self.sub_requestor is None:
            user = self.get_user()
            self.sub_requestor = self.__get_cache_requestor("GET", "/subscriptions", params={"broadcaster_id": user.id})
        response = self.__call_endpoint(self.sub_requestor)
        return [model.Suscription(**x) for x in response["data"] or []]

    @overload
    def get_user(self) -> model.User:
        ...

    @overload
    def get_user(self, login: str) -> Optional[model.User]:
        ...

    def get_user(self, login: Optional[str] = None):
        if login is None:
            requestor = self.users_cache.setdefault("$", self.__get_cache_requestor("GET", "/users"))
        else:
            requestor = self.users_cache.setdefault(
                login, self.__get_cache_requestor("GET", "/users", params={"login": login}))
        response = self.__call_endpoint(requestor)
        users = [model.User(**x) for x in response["data"] or []]
        if login is None:
            self.users_cache[users[0].login] = self.users_cache["$"]
            return users[0]
        user = None if len(users) == 0 else users[0]
        return user

    def get_channel(self, broadcaster_id: str) -> Optional[model.Channel]:
        requestor = self.channel_cache.setdefault(
            broadcaster_id, self.__get_cache_requestor("GET", "/channels", params={"broadcaster_id": broadcaster_id}))
        response = self.__call_endpoint(requestor)
        channels = [model.Channel(**x) for x in response["data"] or []]
        channel = None if len(channels) == 0 else channels[0]
        return channel

    def get_channel_editors(self) -> List[model.ChannelEditor]:
        if self.channel_editors_cache is None:
            user = self.get_user()
            self.channel_editors_cache = self.__get_cache_requestor("GET", "/channels/editors",
                                                                    params={"broadcaster_id": user.id})
        response = self.__call_endpoint(self.channel_editors_cache)
        editors = [model.ChannelEditor(**x) for x in response["data"] or []]
        return editors

    def __get_cache_requestor(self, method, path, params=None):
        return CacheRequest(
            method, "https://api.twitch.tv/helix" + path, params=params, headers={
                "Authorization": f"{self.token.token_type.title()} {self.token.access_token}",
                "Client-Id": Constants.CLIENT_ID
            })

    def stop_(self):
        self.__active = False

    def __del__(self):
        self.__active = False
