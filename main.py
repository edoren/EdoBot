import getpass
import json
import logging
import os
import os.path
import sys
import time
import webbrowser
from enum import Enum
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from posixpath import pardir
from types import SimpleNamespace
from typing import List, Mapping, Optional, Set

import obswebsocket
import obswebsocket.requests
import requests

from config import Config
from data_base import DataBase
from irc import TwitchIRC
from model import AccessToken

gLogger = logging.getLogger("me.edoren.edobot.main")

gClientId = "w2bmwjuyuxyz7hmz5tjpjorlerkn9u"
# client_secret = "cu7s3ke9lrihfas74n42kozphbjtkc"

gBaseDir = os.path.dirname(__file__)


class UserType(Enum):
    BROADCASTER = 1
    MODERATOR = 2
    VIP = 3  # NOT WORKING
    SUBSCRIPTOR = 4
    CHATTER = 4


class TokenRedirectWebServer:
    host: str = "localhost"
    port: int = 3506

    class RequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            if "request_close" in kwargs:
                self.request_close = kwargs["request_close"]
                del kwargs["request_close"]
            kwargs["directory"] = os.path.join(gBaseDir, "www")
            super().__init__(*args, **kwargs)

        def do_PUT(self):
            self.send_response(200)
            self.end_headers()
            content_len = int(self.headers.get("Content-Length"))
            put_body = self.rfile.read(content_len)
            json_body = json.loads(put_body)
            self.request_close(json_body)

    @staticmethod
    def get_redirect_url() -> str:
        return "http://{}:{}".format(TokenRedirectWebServer.host,
                                     TokenRedirectWebServer.port)

    def __init__(self, url: str) -> None:
        self.token: Mapping = {}
        self.url = url

    def run(self) -> AccessToken:
        gLogger.info(f"Opening the URL: {self.url}")
        self.__open_url()
        server_address = (TokenRedirectWebServer.host,
                          TokenRedirectWebServer.port)
        with ThreadingHTTPServer(server_address, TokenRedirectWebServer.RequestHandler) as httpd:
            def request_close(token):
                self.token = token
                httpd.shutdown()

            httpd.RequestHandlerClass = partial(TokenRedirectWebServer.RequestHandler,
                                                request_close=request_close)
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("Keyboard interrupt received, exiting.")
                sys.exit(-1)
        return AccessToken(**self.token)

    def __open_url(self):
        browser = webbrowser.get()
        browser.open_new(self.url)
        print("Could not find a suitable browser, "
              "please open the URL directly:\n{}".format(self.url))


class TwitchService:
    def __init__(self, user_login: str, scope: List[str]):
        self.db = DataBase()
        self.user_login = user_login
        self.scope = scope

        self.token = self.db.get_token_for_user(self.user_login)
        if self.token is not None and set(self.token.scope).intersection(set(self.scope)) != set(self.scope):
            self.__reauthorize()

        self.update_user()

    def __call_endpoint(self, path: str, params: dict = {}):
        while True:
            try:
                request = requests.get(
                    "https://api.twitch.tv/helix" + path,
                    params=params,
                    headers={
                        "Authorization": f"{self.token.token_type.title()} {self.token.access_token}",
                        "Client-Id": gClientId
                    }
                )
                if request.status_code == 200:
                    return request.json()
                else:
                    self.__reauthorize()
            except Exception:
                continue

    def __reauthorize(self, force_verify=True):
        print(f"Please login with {self.user_login}")
        redirect_url = TokenRedirectWebServer.get_redirect_url()
        authenticate_url = (f"https://id.twitch.tv/oauth2/authorize"
                            f"?client_id={gClientId}"
                            f"&redirect_uri={redirect_url}"
                            f"&response_type=token"
                            f"&scope={'+'.join(self.scope)}"
                            f"&force_verify={str(force_verify).lower()}"
                            f"&state={'EdoBot'}")
        self.token = TokenRedirectWebServer(authenticate_url).run()
        self.db.set_user_token(self.user_login, self.token)

    def update_user(self) -> dict:
        response = self.__call_endpoint("/users", params={"login": self.user_login})
        self.user = response["data"][0]
        return self.user

    def get_moderators(self) -> List[dict]:
        response = self.__call_endpoint("/moderation/moderators", params={"broadcaster_id": self.user["id"]})
        return response["data"]

    def get_subscribers(self) -> List[dict]:
        response = self.__call_endpoint("/subscriptions", params={"broadcaster_id": self.user["id"]})
        return response["data"]


class TwitchChat:
    def __init__(self, config_file_path: str):
        self.config = Config(config_file_path)

        if not os.path.exists(config_file_path):
            print("Welcome to the EdorenBot\n")
            print("Please input the following data in order to continue")
            self.config["account"] = input("Account: ")
            use_different_name = input(f"Use '{~self.config['account']}' "
                                       "for the chat [yes/no]: ")
            if use_different_name.lower() != "yes":
                self.config["bot_account"] = input("Chat account: ")
            else:
                self.config["bot_account"] = self.config["account"]

            self.config["obswebsocket"] = {}
            self.config["obswebsocket"]["port"] = input("obs-websocket port [default:4444]: ")
            if (len(~self.config["obswebsocket"]["port"]) == 0):
                self.config["obswebsocket"]["port"] = 4444
            self.config["obswebsocket"]["password"] = getpass.getpass("obs-websocket password: ")

            print()

        account_login = ~self.config["account"]
        bot_account_login = ~self.config["bot_account"]

        self.websocket_client = obswebsocket.obsws("localhost",
                                                   ~self.config["obswebsocket"]["port"],
                                                   ~self.config["obswebsocket"]["password"])

        self.transition_matrix = {
            "Starting": set(),
            "Lobby": set(["Gaming", "AFK"]),
            "Gaming": set(["Lobby"]),
            "AFK": set(["Lobby"]),
            "Ending": set()
        }

        base_scope = [
            "user:read:email",
            "channel:read:subscriptions",
            "moderation:read"
        ]

        bot_scope = [
            "channel:moderate",
            "chat:edit",
            "chat:read",
            "whispers:read",
            "whispers:edit"
        ]

        if account_login == bot_account_login:
            scope = base_scope + bot_scope
            self.host_service = TwitchService(account_login, scope)
            self.bot_service = self.host_service
        else:
            self.host_service = TwitchService(account_login, base_scope)
            self.bot_service = TwitchService(bot_account_login, bot_scope)

        self.irc = TwitchIRC(self.bot_service.user["display_name"],
                             self.bot_service.token.access_token)
        self.irc.subscribe(self.handle_message)
        self.irc.join_channel(self.host_service.user["login"])

    def handle_message(self, data: bytes) -> None:
        text = data.decode("UTF-8").strip('\n\r')
        if text.find('PRIVMSG') < 0:
            return

        message = SimpleNamespace(
            sender=text.split('!', 1)[0][1:],
            text=text.split('PRIVMSG', 1)[1].split(':', 1)[1]
        )

        user_flags: Set[UserType] = {UserType.CHATTER}

        if self.host_service.user["login"] == message.sender:
            user_flags.add(UserType.BROADCASTER)
            user_flags.add(UserType.MODERATOR)
            user_flags.add(UserType.SUBSCRIPTOR)
            user_flags.add(UserType.VIP)

        for user in self.mods:
            if user["user_login"] == message.sender:
                user_flags.add(UserType.MODERATOR)

        for user in self.subs:
            if user["user_login"] == message.sender:
                user_flags.add(UserType.SUBSCRIPTOR)

        if UserType.MODERATOR in user_flags and message.text.startswith("!scene"):
            args = message.text.strip().split(" ")[1:2]
            if len(args) > 0:
                scenes_request = self.websocket_client.call(obswebsocket.requests.GetSceneList())

                scenes = scenes_request.getScenes()

                # Find a suitable scene target name
                target_scene = None
                for scene in scenes:
                    if scene["name"].lower() == args[0].lower():
                        target_scene = scene["name"]

                if target_scene is not None:
                    current_scene = scenes_request.getCurrentScene()
                    if current_scene in self.transition_matrix:
                        if target_scene in self.transition_matrix[current_scene]:
                            gLogger.info(f"[{message.sender}] Transitioning: {current_scene} -> {target_scene}")
                            self.websocket_client.call(obswebsocket.requests.SetCurrentScene(target_scene))
                    else:
                        gLogger.error(f"Error: Scene '{current_scene}' not found in transition matrix")

    def run(self):
        gLogger.info("Starting Bot loop")
        self.websocket_client.connect()
        self.mods = self.host_service.get_moderators()
        self.subs = self.host_service.get_subscribers()
        self.irc.start()
        gLogger.info("Bot started")

    def stop(self):
        gLogger.info("Stopping Bot loop")
        self.irc.stop()
        self.websocket_client.disconnect()
        gLogger.info("Bot stopped")


if __name__ == "__main__":
    config_file_path = os.path.join(gBaseDir, "config.json")

    handlers = [
        logging.FileHandler("out.log", "a"),
        logging.StreamHandler(None)
    ]

    logging.basicConfig(format="[%(asctime)s] %(levelname)s - %(threadName)s[%(thread)d] - %(name)s - %(message)s",
                        level=logging.INFO, handlers=handlers)

    bot = TwitchChat(config_file_path)

    try:
        gLogger.info("EdorenBot 1.0")
        bot.run()

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bot.stop()
