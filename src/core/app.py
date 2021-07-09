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
from typing import Any, Callable, List, Mapping, MutableMapping, Optional, Set, Type

import model
import twitch
from obs import OBSInterface, OBSWebSocket, StreamlabsOBS

from .chat_component import ChatComponent
from .config import Config
from .constants import Constants
from .data_base import DataBase

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
            content_len = int(self.headers["Content-Length"])
            put_body = self.rfile.read(content_len)
            json_body = json.loads(put_body)
            self.token_received(model.AccessToken(**json_body))

        def log_message(self, format, *args):
            pass

    def __init__(self, token_listener: Callable[[model.AccessToken], None]) -> None:
        super().__init__(name="TokenRedirectWebServerThread")
        self.httpd = None
        self.token_listener = token_listener

    def run(self) -> None:
        server_address = (TokenRedirectWebServer.host, TokenRedirectWebServer.port)
        handler_class = partial(TokenRedirectWebServer.RequestHandler, token_received=self.token_listener)
        with ThreadingHTTPServer(server_address, handler_class) as self.httpd:
            if self.httpd is not None:
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

        self.available_components: MutableMapping[str, Type[ChatComponent]] = {}
        self.failed_components: List[str] = []
        self.active_components: MutableMapping[str, ChatComponent] = {}
        self.components_lock = threading.Lock()
        self.update_available_components()

        self.host_scope = [
            "bits:read", "channel:moderate", "channel:read:editors", "channel:read:redemptions",
            "channel:read:subscriptions", "moderation:read", "user:read:email", "whispers:read"
        ]
        self.bot_scope = ["channel:moderate", "chat:edit", "chat:read", "whispers:read", "whispers:edit"]
        self.host_scope.sort()
        self.bot_scope.sort()

        self.executor: Optional[ThreadPoolExecutor] = None

        self.token_web_server: Optional[TokenRedirectWebServer] = None

        # callbacks
        self.started: Optional[Callable[[], None]] = None
        self.stopped: Optional[Callable[[], None]] = None
        self.component_added: Optional[Callable[[ChatComponent], None]] = None
        self.component_removed: Optional[Callable[[ChatComponent], None]] = None
        self.host_connected: Optional[Callable[[model.User], None]] = None
        self.host_disconnected: Optional[Callable[[], None]] = None
        self.bot_connected: Optional[Callable[[model.User], None]] = None
        self.bot_disconnected: Optional[Callable[[], None]] = None

        self.current_components = self.config["components"].setdefault([])

        self.obs_choice = self.config["obs_choice"].setdefault("obswebsocket")
        self.config["obswebsocket"].setdefault({"host": "localhost", "port": 4444, "password": "changeme"})
        self.config["slobs"].setdefault({"host": "localhost", "port": 59650, "token": ""})

        # Load the components and remove the repeated items mantaining the order
        seen = set()
        self.current_components = [x for x in self.current_components if not (x in seen or seen.add(x))]

        if self.obs_choice == "slobs":
            config = ~self.config["slobs"]
            self.obs_client: OBSInterface = StreamlabsOBS(config["host"], config["port"], config["token"])
            self.obs_client.set_config(~self.config["slobs"])
            self.obs_client.connect()
        else:
            config = ~self.config["obswebsocket"]
            self.obs_client: OBSInterface = OBSWebSocket(config["host"], config["port"], config["password"])
            self.obs_client.set_config(~self.config["obswebsocket"])
            self.obs_client.connect()

    #################################################################
    # Listeners
    #################################################################

    def token_received(self, token: model.AccessToken):
        if token.state[0] == "host":
            self.host_twitch_service = twitch.Service(token)
            if self.host_connected:
                self.host_connected(self.host_twitch_service.get_user())
        elif token.state[0] == "bot":
            self.bot_twitch_service = twitch.Service(token)
            if self.bot_connected:
                self.bot_connected(self.bot_twitch_service.get_user())
        self.db.set_user_token(token.state[0], token)
        if self.host_twitch_service is not None and self.bot_twitch_service is not None:
            self.__stop_token_web_server()

    def handle_message(self, sender: str, tags: twitch.PrivateMsgTags, text: str) -> None:
        if self.host_twitch_service is None or self.bot_twitch_service is None:
            return

        user_types: Set[model.UserType] = {model.UserType.CHATTER}

        if self.host_twitch_service.get_user().login == sender:
            user_types.add(model.UserType.BROADCASTER)
            user_types.add(model.UserType.EDITOR)
            user_types.add(model.UserType.MODERATOR)
            user_types.add(model.UserType.VIP)

        user = self.host_twitch_service.get_user(sender)

        if user is None:
            gLogger.warning(f"User '{sender}' could not be found")
            return

        if tags.mod:
            user_types.add(model.UserType.MODERATOR)

        if "vip" in tags.badges:
            user_types.add(model.UserType.VIP)

        if model.UserType.VIP in user_types or model.UserType.MODERATOR in user_types:
            channel_editors = self.host_twitch_service.get_channel_editors()
            for editor in channel_editors:
                if editor.user_id == user.id:
                    user_types.add(model.UserType.EDITOR)

        if "subscriber" in tags.badges:
            user_types.add(model.UserType.SUBSCRIPTOR)

        is_command = text.startswith("!")
        with self.components_lock:
            for component in self.active_components.values():
                comp_command = component.get_command()
                if comp_command is not None:
                    if is_command:
                        command_pack = text.lstrip("!").split(" ", 1)
                        command = command_pack[0]
                        message = command_pack[1] if len(command_pack) > 1 else ""
                        if ((isinstance(comp_command, str) and command.lower() == comp_command.lower())
                                or (isinstance(comp_command, list) and command in comp_command)):
                            self.__secure_component_method_call(component, "process_message", message, user, user_types)
                else:
                    self.__secure_component_method_call(component, "process_message", text, user, user_types)

    def handle_event(self, event_type: model.EventType, metadata: Any):
        if self.host_twitch_service is None or self.bot_twitch_service is None:
            return
        with self.components_lock:
            for component in self.active_components.values():
                self.__secure_component_method_call(component, "process_event", event_type, metadata)

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

    def get_available_components(self) -> Mapping[str, Type[ChatComponent]]:
        return self.available_components

    def get_active_components(self) -> Mapping[str, ChatComponent]:
        return self.active_components

    def set_obs_choice(self, choice: str) -> None:
        self.obs_choice = choice

    def get_obs_choice(self) -> str:
        return self.obs_choice

    def set_obs_config(self, host: str, port: int, password: str):
        config = {"host": host, "port": port, "password": password}
        self.config["obswebsocket"] = config
        self.obs_client.set_config(config)

    def get_obs_config(self):
        return ~self.config["obswebsocket"]

    def update_available_components(self):
        self.available_components = {}

        search_folders = [
            os.path.join(Constants.EXECUTABLE_DIRECTORY, "components"),
            os.path.join(Constants.SAVE_DIRECTORY, "components")
        ]

        def import_component(file_path, module_name):
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None:
                # TODO: Report error
                return
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)  # type: ignore
            for class_name, class_type in inspect.getmembers(module, inspect.isclass):
                try:
                    if issubclass(class_type, ChatComponent) and class_type is not ChatComponent:
                        component_id = class_type.get_metadata().id
                        if component_id in self.available_components:
                            gLogger.error(f"Error loading component with id '{component_id}' for "
                                          f"class name '{class_name}': another component has the same id")
                        self.available_components[component_id] = class_type
                except NotImplementedError:
                    class_abstract_methods = [a for a in class_type.__abstractmethods__]  # type: ignore
                    gLogger.error(f"Error in file '{file_path}' class '{class_name}' does not "
                                  f"implement all abstract methods: {class_abstract_methods}")

        for components_folder in search_folders:
            if not os.path.isdir(components_folder):
                try:
                    os.makedirs(components_folder)
                except Exception:
                    pass
                continue

            for filename in os.listdir(components_folder):
                full_path = os.path.join(components_folder, filename)
                if os.path.isfile(full_path):
                    basename, extension = os.path.splitext(filename)
                    if extension in (".pyc", ".py"):
                        module_name = f"components.{basename}"
                        import_component(full_path, module_name)
                elif os.path.isdir(full_path):
                    for filename in os.listdir(full_path):
                        if filename in ("__init__.pyc", "__init__.py"):
                            basename = os.path.basename(full_path)
                            module_name = f"components.{basename}"
                            file_path = os.path.join(full_path, filename)
                            import_component(file_path, module_name)

    def add_component(self, component_id: str) -> Optional[ChatComponent]:
        if component_id in self.active_components:
            return

        class_type = None
        for comp_id in self.available_components.keys():
            if component_id == comp_id:
                class_type = self.available_components[comp_id]

        if class_type is None:
            gLogger.error(f"Error loading component with id '{component_id}' not found")
            return

        component_name = class_type.get_metadata().name
        gLogger.info(f"Adding component '{component_name}' with class name '{class_type.__name__}'.")
        if component_id in self.active_components:
            gLogger.error(f"Component with name '{component_name}' already exists. Adding failed.")
            return

        try:
            instance = class_type()  # type: ignore
        except (NotImplementedError, TypeError) as e:
            gLogger.error(f"Error loading component with id '{component_id}': {e}")
            return
        with self.components_lock:
            self.active_components[component_id] = instance
            if component_id not in self.current_components:
                self.current_components += [component_id]
                self.config["components"] = self.current_components
            if self.component_added:
                self.component_added(instance)
            if self.has_started and self.chat_service is not None and self.host_twitch_service is not None:
                instance.config_component(config=self.__get_component_config(instance.get_metadata().id),
                                          obs=self.obs_client, chat=self.chat_service, twitch=self.host_twitch_service)
                succeded = self.__secure_component_method_call(instance, "start")
                if not succeded:
                    self.__secure_component_method_call(instance, "stop")
            return instance

    def remove_component(self, component_id: str) -> None:
        with self.components_lock:
            component = self.active_components[component_id]
            self.__secure_component_method_call(component, "stop")
            gLogger.info(f"Removing component '{component.get_metadata().name}' with class name "
                         f"'{component.__class__.__name__}'.")
            self.current_components.remove(component_id)
            self.config["components"] = self.current_components
            if self.component_removed:
                self.component_removed(self.active_components[component_id])
            del self.active_components[component_id]

    def start(self):
        def __run(self: App):
            for component_id in self.current_components:
                self.add_component(component_id)

            host_token = self.db.get_token_for_user("host")
            bot_token = self.db.get_token_for_user("bot")
            if host_token:
                host_token.scope.sort()
            if bot_token:
                bot_token.scope.sort()

            self.host_twitch_service = None
            self.bot_twitch_service = None

            if self.is_running and host_token is not None and host_token.scope == self.host_scope:
                try:
                    self.host_twitch_service = twitch.Service(host_token)
                    if self.host_connected:
                        self.host_connected(self.host_twitch_service.get_user())
                except twitch.service.UnauthenticatedException:
                    self.db.remove_user("host")
                except Exception as e:
                    gLogger.error(''.join(traceback.format_tb(e.__traceback__)))

            if self.is_running and bot_token is not None and bot_token.scope == self.bot_scope:
                try:
                    self.bot_twitch_service = twitch.Service(bot_token)
                    if self.bot_connected:
                        self.bot_connected(self.bot_twitch_service.get_user())
                except twitch.service.UnauthenticatedException:
                    self.db.remove_user("bot")
                except Exception as e:
                    gLogger.error(''.join(traceback.format_tb(e.__traceback__)))

            # Waiting for tokens available
            gLogger.info("Waiting for tokens available to start Services")
            if self.is_running and (self.host_twitch_service is None or self.bot_twitch_service is None):
                self.__start_token_web_server()

            while self.is_running:
                if self.host_twitch_service is not None and self.bot_twitch_service is not None:
                    break
                time.sleep(1)
            else:  # Check if it's running as it can be canceled before reaching the start
                return

            with self.start_stop_lock:
                self.chat_service = twitch.Chat(self.bot_twitch_service.get_user().display_name,
                                                self.bot_twitch_service.token.access_token,
                                                self.host_twitch_service.get_user().login)
                self.pubsub_service = twitch.PubSub(self.host_twitch_service.get_user().id,
                                                    self.host_twitch_service.token.access_token)

                with self.components_lock:
                    for instance in self.active_components.values():
                        instance.config_component(config=self.__get_component_config(instance.get_metadata().id),
                                                  obs=self.obs_client, chat=self.chat_service,
                                                  twitch=self.host_twitch_service)
                        succeded = self.__secure_component_method_call(instance, "start")
                        if not succeded:
                            self.__secure_component_method_call(instance, "stop")

                gLogger.info("Bot started")

            self.chat_service.start()
            self.chat_service.subscribe(self.handle_message)
            self.chat_service.subscribe_events(self.handle_event)
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
            gLogger.info(f"Starting {Constants.APP_NAME} ({Constants.APP_VERSION}), please wait...")
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
                with self.components_lock:
                    for component in self.active_components.values():
                        self.__secure_component_method_call(component, "stop")
                    self.active_components.clear()
                if self.chat_service is not None:
                    self.chat_service.stop()
                if self.pubsub_service is not None:
                    self.pubsub_service.stop()
                if self.stopped:
                    self.stopped()
                self.chat_service = None
                self.pubsub_service = None
                gLogger.info("Bot stopped")
            self.has_started = False

    def shutdown(self):
        if not self.is_running:
            return
        self.config["components"] = self.current_components
        if self.bot_twitch_service is not None:
            self.bot_twitch_service.stop_()
            self.bot_twitch_service = None
        if self.host_twitch_service is not None:
            self.host_twitch_service.stop_()
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
        component_config_file = os.path.join(Constants.CONFIG_DIRECTORY, "components", f"{component_id}.json")
        return Config(component_config_file)

    @staticmethod
    def __secure_component_method_call(component: ChatComponent, method_name: str, *args: Any, **kwargs: Any) -> bool:
        try:
            method = getattr(component, method_name)
            method(*args, **kwargs)
            return True
        except Exception as e:
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            gLogger.error(f"Error in component '{component.get_metadata().name}': {e}\n{traceback_str}")
        return False
