import logging
import time
from typing import Any, List, Mapping

import requests

import model
from core.constants import Constants
from model.access_token import AccessToken

__all__ = ["Service"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class UnauthenticatedException(Exception):
    pass


class Service:
    def __init__(self, token: AccessToken):
        self.token = token

        self.__active = True

        self.user = self.get_users()[0]
        self.chatters: List[model.User] = []

    def __call_endpoint(self, path: str, params: Mapping[str, Any] = {}):
        retry_time = 1
        while self.__active:
            request_url = "https://api.twitch.tv/helix" + path
            try:
                request = requests.get(
                    request_url,
                    params=params,
                    headers={
                        "Authorization": f"{self.token.token_type.title()} {self.token.access_token}",
                        "Client-Id": Constants.CLIENT_ID
                    }
                )
                if request.status_code == 200:
                    return request.json()
                elif request.status_code == 401:
                    raise UnauthenticatedException("Unauthenticated: Missing/invalid Token")
                else:
                    gLogger.error(f"Error reaching url '{request_url}' failed: {request.json()}")
                    return {"data": None}
            except UnauthenticatedException as e:
                raise e
            except Exception as e:
                gLogger.error(f"Error reaching url '{request_url}' retying in {retry_time} seconds: {e}")
                time.sleep(retry_time)
                retry_time *= 2
                continue
        return {"data": None}

    def get_moderators(self) -> List[model.Moderator]:
        response = self.__call_endpoint("/moderation/moderators", params={"broadcaster_id": self.user.id})
        return [model.Moderator(**x) for x in response["data"] or []]

    def get_subscribers(self) -> List[model.Suscription]:
        response = self.__call_endpoint("/subscriptions", params={"broadcaster_id": self.user.id})
        return [model.Suscription(**x) for x in response["data"] or []]

    def get_users(self, names: List[str] = []) -> List[model.User]:
        response = self.__call_endpoint("/users", params={"login[]": names})
        return [model.User(**x) for x in response["data"] or []]

    def get_chatters(self):
        pass

    def __del__(self):
        self.__active = False
