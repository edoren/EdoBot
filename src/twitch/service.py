import json
import logging
import os.path
import webbrowser
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, List, Mapping

import requests

import model
from core.app import App
from core.data_base import DataBase

__all__ = ["Service"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class TokenRedirectWebServer:
    host: str = "localhost"
    port: int = 3506

    class RequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            if "request_close" in kwargs:
                self.request_close = kwargs["request_close"]
                del kwargs["request_close"]
            kwargs["directory"] = os.path.join(App.EXECUTABLE_DIRECTORY, "www")
            super().__init__(*args, **kwargs)

        def do_PUT(self):
            self.send_response(200)
            self.end_headers()
            content_len = int(self.headers.get("Content-Length"))
            put_body = self.rfile.read(content_len)
            json_body = json.loads(put_body)
            self.request_close(json_body)

        def log_message(self, format, *args):
            pass

    @staticmethod
    def get_redirect_url() -> str:
        return "http://{}:{}".format(TokenRedirectWebServer.host,
                                     TokenRedirectWebServer.port)

    def __init__(self, url: str) -> None:
        self.token: Mapping["str", Any] = {}
        self.url = url

    def run(self) -> model.AccessToken:
        self.__open_url()
        server_address = (TokenRedirectWebServer.host, TokenRedirectWebServer.port)
        with ThreadingHTTPServer(server_address, TokenRedirectWebServer.RequestHandler) as httpd:
            def request_close(token):
                self.token = token
                httpd.shutdown()

            httpd.RequestHandlerClass = partial(TokenRedirectWebServer.RequestHandler,
                                                request_close=request_close)
            httpd.serve_forever()
        return model.AccessToken(**self.token)

    def __open_url(self):
        browser = webbrowser.get()
        try:
            browser.open_new(self.url)
        except Exception:
            print("Could not find a suitable browser, please open the URL directly:\n{}".format(self.url))


class Service:
    def __init__(self, user_login: str, scope: List[str]):
        self.db = DataBase(App.SAVE_DIRECTORY)
        self.user_login = user_login
        self.scope = scope

        self.token = self.db.get_token_for_user(self.user_login)
        if self.token is None or set(self.token.scope).intersection(set(self.scope)) != set(self.scope):
            self.__reauthorize()

        self.user = self.get_users([self.user_login])[0]
        self.chatters: List[model.User] = []

    def __call_endpoint(self, path: str, params: Mapping[str, Any] = {}):
        retry_time = 0.5
        while True:
            request_url = "https://api.twitch.tv/helix" + path
            try:
                request = requests.get(
                    request_url,
                    params=params,
                    headers={
                        "Authorization": f"{self.token.token_type.title()} {self.token.access_token}",
                        "Client-Id": App.CLIENT_ID
                    }
                )
                if request.status_code == 200:
                    return request.json()
                elif request.status_code == 401:
                    self.__reauthorize()
                else:
                    gLogger.error(f"Error reaching url '{request_url}' failed: {request.json()}")
                    return {"data": None}
            except Exception as e:
                gLogger.error(f"Error reaching url '{request_url}' retying in {retry_time} seconds: {e}")
                time.sleep(retry_time)
                retry_time *= 2
                continue

    def __reauthorize(self, force_verify=True):
        input(f"You will be redirected to the browser to login with '{self.user_login}' [Press Enter]")
        redirect_url = TokenRedirectWebServer.get_redirect_url()
        authenticate_url = (f"https://id.twitch.tv/oauth2/authorize"
                            f"?client_id={App.CLIENT_ID}"
                            f"&redirect_uri={redirect_url}"
                            f"&response_type=token"
                            f"&scope={'+'.join(self.scope)}"
                            f"&force_verify={str(force_verify).lower()}"
                            f"&state={'EdoBot'}")
        self.token = TokenRedirectWebServer(authenticate_url).run()
        self.db.set_user_token(self.user_login, self.token)

    def get_moderators(self) -> List[model.Moderator]:
        response = self.__call_endpoint("/moderation/moderators", params={"broadcaster_id": self.user.id})
        ret = [model.Moderator(**x) for x in response["data"] or []]
        return ret

    def get_subscribers(self) -> List[model.Suscription]:
        response = self.__call_endpoint("/subscriptions", params={"broadcaster_id": self.user.id})
        ret = [model.Suscription(**x) for x in response["data"] or []]
        return ret

    def get_users(self, names: List[str]) -> List[model.User]:
        response = self.__call_endpoint("/users", params={"login[]": names})
        ret = [model.User(**x) for x in response["data"] or []]
        return ret or []

    def get_chatters(self):
        pass
