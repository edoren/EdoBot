import importlib
import importlib.util
import inspect
import json
import logging
import os
import os.path
import signal
import sys
import threading
import traceback
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Mapping, MutableMapping, Optional, Set

import requests

from component import TwitchChatComponent
from config import Config
from data_base import DataBase
from model import AccessToken, User
from twitch_irc import TwitchIRC
from user_type import UserType

gLogger = logging.getLogger("me.edoren.edobot.main")

gClientId = "w2bmwjuyuxyz7hmz5tjpjorlerkn9u"

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    gBaseDir = os.path.dirname(sys.executable)
    sys.path.append(os.path.join(gBaseDir, "modules"))
else:
    gBaseDir = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    print(gBaseDir)


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

        def log_message(self, format, *args):
            pass

    @staticmethod
    def get_redirect_url() -> str:
        return "http://{}:{}".format(TokenRedirectWebServer.host,
                                     TokenRedirectWebServer.port)

    def __init__(self, url: str) -> None:
        self.token: Mapping = {}
        self.url = url

    def run(self) -> AccessToken:
        self.__open_url()
        server_address = (TokenRedirectWebServer.host, TokenRedirectWebServer.port)
        with ThreadingHTTPServer(server_address, TokenRedirectWebServer.RequestHandler) as httpd:
            def request_close(token):
                self.token = token
                httpd.shutdown()

            httpd.RequestHandlerClass = partial(TokenRedirectWebServer.RequestHandler,
                                                request_close=request_close)
            httpd.serve_forever()
        return AccessToken(**self.token)

    def __open_url(self):
        browser = webbrowser.get()
        try:
            browser.open_new(self.url)
        except Exception:
            print("Could not find a suitable browser, please open the URL directly:\n{}".format(self.url))


class TwitchService:
    def __init__(self, user_login: str, scope: List[str]):
        self.db = DataBase()
        self.user_login = user_login
        self.scope = scope

        self.token = self.db.get_token_for_user(self.user_login)
        if self.token is None or set(self.token.scope).intersection(set(self.scope)) != set(self.scope):
            self.__reauthorize()

        self.user = self.get_users([self.user_login])[0]
        self.chatters: List[User] = []

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
            except Exception as e:
                gLogger.error("Error calling service: ", e)
                continue

    def __reauthorize(self, force_verify=True):
        input(f"You will be redirected to the browser to login with '{self.user_login}' [Press Enter]")
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

    def get_moderators(self) -> List[dict]:
        response = self.__call_endpoint("/moderation/moderators", params={"broadcaster_id": self.user.id})
        return response["data"]

    def get_subscribers(self) -> List[dict]:
        response = self.__call_endpoint("/subscriptions", params={"broadcaster_id": self.user.id})
        return response["data"]

    def get_users(self, names: List[str]) -> List[User]:
        response = self.__call_endpoint("/users", params={"login[]": names})
        ret = [User(**x) for x in response["data"]]
        return ret

    def get_chatters(self):
        pass


class TwitchChat:
    def __init__(self, config_file_path: str):
        self.irc: Optional[TwitchIRC] = None
        self.config = Config(config_file_path)
        self.components: MutableMapping[str, TwitchChatComponent] = {}
        self.start_stop_lock = threading.Lock()

        if not os.path.exists(config_file_path):
            print("Please input the following data in order to continue:\n")

            self.config["account"] = input("Account: ")
            use_different_name = input(f"Use '{~self.config['account']}' for the chat [yes/no]: ")
            if use_different_name.lower() != "yes":
                self.config["bot_account"] = input("Chat account: ")

            self.config["components"] = {}

            print(flush=True)

        account_login = ~self.config["account"]
        bot_account_login = ~self.config["bot_account"]

        host_scope = ["user:read:email",  "channel:read:subscriptions", "moderation:read"]
        bot_scope = ["channel:moderate", "chat:edit", "chat:read", "whispers:read", "whispers:edit"]
        if bot_account_login is None:
            scope = host_scope + bot_scope
            self.host_service = TwitchService(account_login, scope)
            self.bot_service = self.host_service
        else:
            self.host_service = TwitchService(account_login, host_scope)
            self.bot_service = TwitchService(bot_account_login, bot_scope)

        components_config = self.config["components"]

        components_folder = os.path.join(gBaseDir, "components")
        if os.path.isdir(components_folder):
            for filename in os.listdir(components_folder):
                file_path = os.path.join(components_folder, filename)
                filename, extension = os.path.splitext(filename)
                if extension == ".py":
                    module_name = f"components.{filename}"
                elif extension == ".pyc":
                    module_name = f"components.{filename.split('.')[0]}"
                else:
                    continue
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)  # type: ignore
                for name, class_type in inspect.getmembers(module, inspect.isclass):
                    if issubclass(class_type, TwitchChatComponent) and class_type is not TwitchChatComponent:
                        component_name = class_type.get_name()
                        if component_name not in ~components_config:
                            components_config[component_name] = {}
                        gLogger.info(f"Adding component '{component_name}' with class name '{name}'")
                        self.components[component_name] = class_type(components_config[component_name])

    def handle_message(self, data: bytes) -> None:
        text = data.decode("UTF-8").strip('\n\r')
        if text.find('PRIVMSG') < 0:
            return

        message_sender = text.split('!', 1)[0][1:]
        message_text = text.split('PRIVMSG', 1)[1].split(':', 1)[1]

        user_flags: Set[UserType] = {UserType.CHATTER}

        if self.host_service.user.login == message_sender:
            user_flags.add(UserType.BROADCASTER)
            user_flags.add(UserType.MODERATOR)
            user_flags.add(UserType.SUBSCRIPTOR)
            user_flags.add(UserType.VIP)

        for user in self.mods:
            if user["user_login"] == message_sender:
                user_flags.add(UserType.MODERATOR)

        for user in self.subs:
            if user["user_login"] == message_sender:
                user_flags.add(UserType.SUBSCRIPTOR)

        args = message_text.strip().split(" ")
        command = args[0].strip("!")
        component_args = args[1:]
        for name, component in self.components.items():
            if command == component.get_command():
                user = self.host_service.get_users([message_sender])[0]
                try:
                    component.process_command(component_args, user, user_flags)
                except Exception as e:
                    traceback_str = ''.join(traceback.format_tb(e.__traceback__))
                    gLogger.error(f"Error in component '{name}': {e}\n{traceback_str}")
                    # TODO: POP ITEMS

    def run(self):
        with self.start_stop_lock:
            if self.irc is not None:
                gLogger.info("Bot already started, stop it first")
                return
            gLogger.info("Starting bot, please wait...")
            self.irc = TwitchIRC(self.bot_service.user.display_name, self.bot_service.token.access_token)
            self.irc.subscribe(self.handle_message)
            self.irc.join_channel(self.host_service.user.login)
            self.mods = self.host_service.get_moderators()
            self.subs = self.host_service.get_subscribers()
            for name, component in self.components.items():
                try:
                    component.start()
                except Exception as e:
                    traceback_str = ''.join(traceback.format_tb(e.__traceback__))
                    gLogger.error(f"Error in component '{name}': {e}\n{traceback_str}")
                    # TODO: POP ITEMS
            gLogger.info("Bot started")
        self.irc.run()

    def stop(self):
        with self.start_stop_lock:
            if self.irc is None:
                # gLogger.warning("Bot already stopped")
                return
            gLogger.info("Stopping bot, please wait...")
            self.irc.stop()
            self.irc = None
            for name, component in self.components.items():
                try:
                    component.stop()
                except Exception as e:
                    traceback_str = ''.join(traceback.format_tb(e.__traceback__))
                    gLogger.error(f"Error in component '{name}': {e}\n{traceback_str}")
            gLogger.info("Bot stopped")


if __name__ == "__main__":
    config_file_path = os.path.join(gBaseDir, "config.json")

    handlers = []
    format_txt = "%(threadName)s %(levelname)s %(name)s - %(message)s"

    file_handler = logging.FileHandler("out.log", "a")
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(process)s " + format_txt, "%Y-%m-%d %H:%M:%S %z"))
    handlers.append(file_handler)

    stream_handler = logging.StreamHandler(None)
    stream_handler.setFormatter(logging.Formatter(format_txt))
    handlers.append(stream_handler)

    logging.basicConfig(level=logging.INFO, handlers=handlers)

    print("------------------------------------------------------------")
    print("------------------------ EdoBot 1.0 ------------------------")
    print("------------------------------------------------------------", flush=True)

    if __debug__:
        print(f"Debug info: [PID: {os.getpid()}]")

    try:
        bot = TwitchChat(config_file_path)

        def signal_handler(sig, frame):
            if sig == signal.SIGINT:
                if os.name != "posix":
                    print("^C")
                if bot is not None:
                    bot.stop()

        signal.signal(signal.SIGINT, signal_handler)
        bot.run()
    except SyntaxError as e:
        raise e
    except KeyboardInterrupt:
        pass
    except Exception as e:
        traceback_str = ''.join(traceback.format_tb(e.__traceback__))
        gLogger.critical(f"Critical error: {e}\n{traceback_str}")
