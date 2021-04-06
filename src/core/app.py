import importlib
import importlib.util
import inspect
import json
import logging
import os
import os.path
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import (Any, Callable, List, Mapping, MutableMapping, Optional,
                    Set, Type)

import model
import twitch
from core.data_base import DataBase
from core.obswrapper import OBSWrapper

from .config import Config
from .constants import Constants

__all__ = ["App"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class TokenRedirectWebServer(threading.Thread):
    host: str = ""
    port: int = 3506

    class RequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self.token_received = kwargs["token_received"]
            del kwargs["token_received"]
            kwargs["directory"] = os.path.join(Constants.DATA_DIRECTORY, "www")
            super().__init__(*args, **kwargs)

        def do_PUT(self):
            self.send_response(200)
            self.end_headers()
            content_len = int(self.headers.get("Content-Length"))  # type: ignore
            put_body = self.rfile.read(content_len)
            json_body = json.loads(put_body)
            self.token_received(model.AccessToken(**json_body))

        # def log_message(self, format, *args):
        #     pass

    def __init__(self, token_listener: Callable[[model.AccessToken], None]) -> None:
        super().__init__(name="TokenRedirectWebServerThread")
        self.httpd = None
        self.token_listener = token_listener

    def run(self) -> None:
        server_address = (TokenRedirectWebServer.host, TokenRedirectWebServer.port)
        handler_class = partial(TokenRedirectWebServer.RequestHandler, token_received=self.token_listener)
        with ThreadingHTTPServer(server_address, handler_class) as self.httpd:
            self.httpd.serve_forever()

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()


class App:
    def __init__(self):
        self.is_running = False
        self.has_started = False
        self.config = Config(os.path.join(Constants.CONFIG_DIRECTORY, "settings.json"))
        self.start_stop_lock = threading.Lock()

        self.host_twitch_service = None
        self.bot_twitch_service = None
        self.db = DataBase(Constants.SAVE_DIRECTORY)

        self.chat_service = None
        self.pubsub_service = None

        self.obs_client = OBSWrapper()

        self.available_components: MutableMapping[str, Type[twitch.ChatComponent]] = {}
        self.failed_components: List[str] = []
        self.active_components: MutableMapping[str, twitch.ChatComponent] = {}
        self.components_lock = threading.Lock()
        self.update_available_components()

        self.host_scope = ["bits:read", "channel:moderate", "channel:read:redemptions",
                           "channel:read:subscriptions", "moderation:read", "user:read:email", "whispers:read"]
        self.bot_scope = ["channel:moderate", "chat:edit", "chat:read", "whispers:read", "whispers:edit"]

        self.executor: Optional[ThreadPoolExecutor] = None

        self.token_web_server: Optional[TokenRedirectWebServer] = None
        self.__start_token_web_server()

        # callbacks
        self.started: Optional[Callable[[], None]] = None
        self.stopped: Optional[Callable[[], None]] = None
        self.component_added: Optional[Callable[[twitch.ChatComponent], None]] = None
        self.component_removed: Optional[Callable[[twitch.ChatComponent], None]] = None
        self.host_connected: Optional[Callable[[model.User], None]] = None
        self.host_disconnected: Optional[Callable[[], None]] = None
        self.bot_connected: Optional[Callable[[model.User], None]] = None
        self.bot_disconnected: Optional[Callable[[], None]] = None

        if ~self.config["components"] is None:
            self.config["components"] = []

        if ~self.config["obswebsocket"] is None:
            self.config["obswebsocket"]["host"] = self.obs_client.host
            self.config["obswebsocket"]["port"] = self.obs_client.port
            self.config["obswebsocket"]["password"] = self.obs_client.password

        obswebsocket_config = ~self.config["obswebsocket"]
        self.obs_client.set_config(
            obswebsocket_config["host"],
            obswebsocket_config["port"],
            obswebsocket_config["password"]
        )
        self.obs_client.connect()

    #################################################################
    # Listeners
    #################################################################

    def token_received(self, token: model.AccessToken):
        if token.state[0] == "host":
            self.host_twitch_service = twitch.Service(token)
            if self.host_connected:
                self.host_connected(self.host_twitch_service.user)
        elif token.state[0] == "bot":
            self.bot_twitch_service = twitch.Service(token)
            if self.bot_connected:
                self.bot_connected(self.bot_twitch_service.user)
        self.db.set_user_token(token.state[0], token)
        if self.host_twitch_service is not None and self.bot_twitch_service is not None:
            self.__stop_token_web_server()

    def handle_message(self, sender: str, text: str) -> None:
        if self.host_twitch_service is None or self.bot_twitch_service is None:
            return

        user_types: Set[twitch.UserType] = {twitch.UserType.CHATTER}

        if self.host_twitch_service.user.login == sender:
            user_types.add(twitch.UserType.BROADCASTER)
            user_types.add(twitch.UserType.MODERATOR)
            user_types.add(twitch.UserType.SUBSCRIPTOR)
            user_types.add(twitch.UserType.VIP)

        for user in self.mods:
            if user.user_login == sender:
                user_types.add(twitch.UserType.MODERATOR)

        for user in self.subs:
            if user.user_login == sender:
                user_types.add(twitch.UserType.SUBSCRIPTOR)

        user = self.host_twitch_service.get_users([sender])[0]

        is_command = text.startswith("!")
        with self.components_lock:
            for component in self.active_components.values():
                comp_command = component.get_command()
                if is_command:
                    command_pack = text.lstrip("!").split(" ", 1)
                    command = command_pack[0]
                    message = command_pack[1] if len(command_pack) > 1 else ""
                    if ((isinstance(comp_command, str) and command == comp_command) or
                            (isinstance(comp_command, list) and command in comp_command)):
                        self.__secure_component_method_call(component, "process_message", message,
                                                            user, user_types)
                elif comp_command is None:
                    self.__secure_component_method_call(component, "process_message", text,
                                                        user, user_types)

    def handle_event(self, topic: str, data: twitch.PubSub.EventTypes):
        if self.host_twitch_service is None or self.bot_twitch_service is None:
            return
        # for component in self.components.values():
        #     component.process_event(topic, data["data"])
        print(topic, data)
        pass

    #################################################################
    # Public
    #################################################################

    def get_host_connect_url(self) -> str:
        return self.__get_auth_url(self.host_scope, "host", True)

    def get_bot_connect_url(self) -> str:
        return self.__get_auth_url(self.bot_scope, "bot", True)

    def reset_host_account(self) -> None:
        self.db.remove_user("host")
        self.host_twitch_service = None
        self.stop()
        self.start()
        if self.host_disconnected:
            self.host_disconnected()

    def reset_bot_account(self) -> None:
        self.db.remove_user("bot")
        self.bot_twitch_service = None
        self.stop()
        self.start()
        if self.bot_disconnected:
            self.bot_disconnected()

    def get_available_components(self) -> Mapping[str, Type[twitch.ChatComponent]]:
        return self.available_components

    def get_active_components(self) -> Mapping[str, twitch.ChatComponent]:
        return self.active_components

    def set_obs_config(self, host: str, port: int, password: str):
        self.config["obswebsocket"]["host"] = host
        self.config["obswebsocket"]["port"] = port
        self.config["obswebsocket"]["password"] = password
        self.obs_client.set_config(host, port, password)

    def get_obs_config(self):
        return ~self.config["obswebsocket"]

    def update_available_components(self):
        self.available_components = {}

        components_folder = os.path.join(Constants.EXECUTABLE_DIRECTORY, "components")
        if not os.path.isdir(components_folder):
            return

        for filename in os.listdir(components_folder):
            file_path = os.path.join(components_folder, filename)
            if os.path.isfile(file_path):
                basename, extension = os.path.splitext(filename)
                if extension in [".py", ".pyc"]:
                    module_name = f"components.{basename}"
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)  # type: ignore
                    for class_name, class_type in inspect.getmembers(module, inspect.isclass):
                        if issubclass(class_type, twitch.ChatComponent) and class_type is not twitch.ChatComponent:
                            component_id = class_type.get_id()
                            if component_id in self.available_components:
                                gLogger.error(f"Error loading component with id '{component_id}' for class name "
                                              f"'{class_name}': another component has the same id")
                            self.available_components[component_id] = class_type
            elif os.path.isdir(file_path):
                pass  # TODO: More complex modules

    def add_component(self, component_id: str) -> Optional[twitch.ChatComponent]:
        if component_id in self.active_components:
            return

        class_type = None
        for comp_id in self.available_components.keys():
            if component_id == comp_id:
                class_type = self.available_components[comp_id]

        if class_type is None:
            gLogger.error(f"Error loading component with id '{component_id}' not found")
            return

        component_name = class_type.get_name()
        gLogger.info(f"Adding component '{component_name}' with class name '{class_type.__name__}'.")
        if component_id in self.active_components:
            gLogger.error(f"Component with name '{component_name}' already exists. Adding failed.")
            return

        instance = class_type()  # type: ignore
        with self.components_lock:
            self.active_components[component_id] = instance
            if component_id not in ~self.config["components"]:
                self.config["components"] = ~self.config["components"] + [component_id]
            if self.component_added:
                self.component_added(instance)
            if self.has_started and self.host_twitch_service is not None:
                instance.config_component(config=self.__get_component_config(instance.get_id()),
                                          obs_client=self.obs_client.get_client(),
                                          twitch=self.host_twitch_service)
                succeded = self.__secure_component_method_call(instance, "start")
                if not succeded:
                    self.__secure_component_method_call(instance, "stop")
            return instance

    def remove_component(self, component_id: str) -> None:
        with self.components_lock:
            component = self.active_components[component_id]
            self.__secure_component_method_call(component, "stop")
            gLogger.info(f"Removing component '{component.get_name()}' with class name "
                         f"'{component.__class__.__name__}'.")
            current_components = ~self.config["components"]
            current_components.remove(component_id)
            self.config["components"] = current_components
            if self.component_removed:
                self.component_removed(self.active_components[component_id])
            del self.active_components[component_id]

    def start(self):
        def __run(self: App):
            for component_id in set(~self.config["components"]):
                self.add_component(component_id)

            host_token = self.db.get_token_for_user("host")
            bot_token = self.db.get_token_for_user("bot")
            if host_token is not None:
                try:
                    self.host_twitch_service = twitch.Service(host_token)
                    if self.host_connected:
                        self.host_connected(self.host_twitch_service.user)
                except twitch.service.UnauthenticatedException:
                    self.db.remove_user("host")
            if bot_token is not None:
                try:
                    self.bot_twitch_service = twitch.Service(bot_token)
                    if self.bot_connected:
                        self.bot_connected(self.bot_twitch_service.user)
                except twitch.service.UnauthenticatedException:
                    self.db.remove_user("bot")

            # Waiting for tokens available
            gLogger.info("Waiting for tokens available to start Services")
            if host_token is None or bot_token is None:
                self.__start_token_web_server()

            while self.is_running:
                if self.host_twitch_service is not None and self.bot_twitch_service is not None:
                    break
                time.sleep(1)
            else:  # Check if it's running as it can be canceled before reaching the start
                return

            with self.start_stop_lock:
                gLogger.info("Starting bot, please wait...")

                self.chat_service = twitch.Chat(self.bot_twitch_service.user.display_name,
                                                self.bot_twitch_service.token.access_token,
                                                self.host_twitch_service.user.login)
                self.pubsub_service = twitch.PubSub(self.host_twitch_service.user.id,
                                                    self.host_twitch_service.token.access_token)

                self.mods = self.host_twitch_service.get_moderators()
                self.subs = self.host_twitch_service.get_subscribers()

                with self.components_lock:
                    for instance in self.active_components.values():
                        instance.config_component(config=self.__get_component_config(instance.get_id()),
                                                  obs_client=self.obs_client.get_client(),
                                                  twitch=self.host_twitch_service)
                        succeded = self.__secure_component_method_call(instance, "start")
                        if not succeded:
                            self.__secure_component_method_call(instance, "stop")

                gLogger.info("Bot started")

            self.chat_service.start()
            self.chat_service.subscribe(self.handle_message)
            self.pubsub_service.start()
            self.pubsub_service.subscribe(self.handle_event)

            self.has_started = True
            if self.started:
                self.started()

        with self.start_stop_lock:
            if self.is_running:
                gLogger.info("Bot already started, stop it first")
                return
            self.is_running = True
            self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="AppWorker")
            self.executor.submit(__run, self)

    def stop(self):
        if not self.is_running:
            return
        with self.start_stop_lock:
            self.is_running = False
            if self.executor is not None:
                self.executor.shutdown(wait=True)
            if self.has_started:
                gLogger.info("Stopping bot, please wait...")
                if self.chat_service is not None:
                    self.chat_service.stop()
                    self.chat_service = None
                if self.pubsub_service is not None:
                    self.pubsub_service.stop()
                    self.pubsub_service = None
                if self.stopped:
                    self.stopped()
                with self.components_lock:
                    for component in self.active_components.values():
                        self.__secure_component_method_call(component, "stop")
                    self.active_components.clear()
                gLogger.info("Bot stopped")
            self.has_started = False

    def shutdown(self):
        if not self.is_running:
            return
        self.bot_twitch_service = None
        self.host_twitch_service = None
        self.stop()
        with self.start_stop_lock:
            gLogger.info("Shutting down bot, please wait...")
            self.obs_client.disconnect()
            self.__stop_token_web_server()
            gLogger.info("Bot shut down")

    #################################################################
    # Private
    #################################################################

    def __start_token_web_server(self):
        if self.token_web_server is None:
            self.token_web_server = TokenRedirectWebServer(self.token_received)
            self.token_web_server.start()

    def __stop_token_web_server(self):
        if self.token_web_server is not None:
            self.token_web_server.stop()
            self.token_web_server = None

    @staticmethod
    def __get_auth_url(scope: List[str], state: str, force_verify=True) -> str:
        return (f"https://id.twitch.tv/oauth2/authorize"
                f"?client_id={Constants.CLIENT_ID}"
                f"&redirect_uri=http://localhost:3506"
                f"&response_type=token"
                f"&scope={'+'.join(scope)}"
                f"&force_verify={str(force_verify).lower()}"
                f"&state={state}")

    @staticmethod
    def __get_component_config(component_id: str) -> Config:
        component_config_file = os.path.join(Constants.CONFIG_DIRECTORY, "components",  f"{component_id}.json")
        return Config(component_config_file)

    @staticmethod
    def __secure_component_method_call(component: twitch.ChatComponent,
                                       method_name: str, *args: Any, **kwargs: Any) -> bool:
        try:
            method = getattr(component, method_name)
            method(*args, **kwargs)
            return True
        except Exception as e:
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            gLogger.error(f"Error in component '{component.get_name()}': {e}\n{traceback_str}")
        return False
