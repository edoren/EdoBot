import getpass
import importlib
import importlib.util
import inspect
import logging
import os
import os.path
import sys
import threading
import traceback
from typing import Any, List, MutableMapping, Set

import twitch
from core.obswrapper import OBSWrapper
from twitch.component import ChatComponent
from twitch.pubsub import PubSub
from twitch.user_type import UserType

from .config import Config
from .constants import Constants

__all__ = ["EdoBot"]

gLogger = logging.getLogger(__name__)


class EdoBot:
    def __init__(self, config_file_path: str):
        self.is_running = False
        self.config = Config(config_file_path)
        self.components: MutableMapping[str, ChatComponent] = {}
        self.failed_components: List[str] = []
        self.start_stop_lock = threading.Lock()
        self.components_lock = threading.Lock()

        self.obs_port = ~self.config["obswebsocket"]["port"]
        self.obs_password = ~self.config["obswebsocket"]["password"]

        if not os.path.exists(config_file_path):
            print("Please input the following data in order to continue:\n")

            self.config["account"] = input("Account: ")
            use_different_name = input(f"Use '{~self.config['account']}' for the chat [yes/no]: ")
            if use_different_name.lower() != "yes":
                self.config["bot_account"] = input("Chat account: ")

            while True:
                try:
                    self.obs_port = int(input("OBS port [4444]: ") or 4444)
                    break
                except ValueError:
                    print("Please input a number or just leave it blank")
            self.obs_password = getpass.getpass("OBS password: ")

            self.config["obswebsocket"]["port"] = self.obs_port
            self.config["obswebsocket"]["password"] = self.obs_password

            self.config["components"] = {}

            print(flush=True)

        account_login = ~self.config["account"]
        bot_account_login = ~self.config["bot_account"]

        host_scope = ["bits:read", "channel:moderate", "channel:read:redemptions",
                      "channel:read:subscriptions", "moderation:read", "user:read:email", "whispers:read"]
        bot_scope = ["channel:moderate", "chat:edit", "chat:read", "whispers:read", "whispers:edit"]
        if bot_account_login is None:
            scope = list(set(host_scope).union(set(bot_scope)))
            self.host_service = twitch.Service(account_login, scope)
            self.bot_service = self.host_service
        else:
            self.host_service = twitch.Service(account_login, host_scope)
            self.bot_service = twitch.Service(bot_account_login, bot_scope)

        self.chat = twitch.Chat(self.bot_service.user.display_name,
                                self.bot_service.token.access_token,
                                self.host_service.user.login)
        self.pubsub = twitch.PubSub(self.host_service.user.id, self.host_service.token.access_token)
        self.obs_client = OBSWrapper(self.obs_port, self.obs_password)

    def add_component(self, name: str) -> None:
        components_config = self.config["components"]

        components_folder = os.path.join(Constants.EXECUTABLE_DIRECTORY, "components")
        if not os.path.isdir(components_folder):
            return

        module_name = None
        file_path = None
        for filename in os.listdir(components_folder):
            file_path = os.path.join(components_folder, filename)
            basename, extension = os.path.splitext(filename)
            if name == basename and extension in [".py", ".pyc"]:
                module_name = f"components.{basename}"
                break

        if module_name is None or file_path is None:
            gLogger.error(f"Error loading component, name '{name}' not found")
            return

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore
        for class_name, class_type in inspect.getmembers(module, inspect.isclass):
            if issubclass(class_type, ChatComponent) and class_type is not ChatComponent:
                component_name = class_type.get_name()
                if component_name not in ~components_config:
                    components_config[component_name] = {}
                gLogger.info(f"Adding component '{component_name}' with class name '{class_name}'.")
                if component_name in self.components:
                    gLogger.error(f"Component with name '{component_name}' already exists. Adding failed.")
                    return
                class_instance = class_type()  # type: ignore
                class_instance.config_component(config=components_config[component_name],
                                                obs_client=self.obs_client.get_client(),
                                                twitch=self.host_service)
                with self.components_lock:
                    if self.is_running:
                        succeded = self.__secure_component_method_call(class_instance, "start")
                        if not succeded:
                            self.__secure_component_method_call(class_instance, "stop")
                        else:
                            self.components[component_name] = class_instance

    def remove_component(self, component_name: str) -> None:
        with self.components_lock:
            component = self.components[component_name]
            self.__secure_component_method_call(component, "stop")
            del self.components[component_name]

    def handle_message(self, sender: str, text: str) -> None:
        user_types: Set[UserType] = {UserType.CHATTER}

        if self.host_service.user.login == sender:
            user_types.add(UserType.BROADCASTER)
            user_types.add(UserType.MODERATOR)
            user_types.add(UserType.SUBSCRIPTOR)
            user_types.add(UserType.VIP)

        for user in self.mods:
            if user.user_login == sender:
                user_types.add(UserType.MODERATOR)

        for user in self.subs:
            if user.user_login == sender:
                user_types.add(UserType.SUBSCRIPTOR)

        user = self.host_service.get_users([sender])[0]

        is_command = text.startswith("!")
        with self.components_lock:
            for _, component in self.components.items():
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

    def handle_event(self, topic: str, data: PubSub.EventTypes):
        # for component in self.components.values():
        #     component.process_event(topic, data["data"])
        print(topic, data)
        pass

    def run(self):
        if self.is_running:
            gLogger.info("Bot already started, stop it first")
            return

        self.is_running = True

        with self.start_stop_lock:
            gLogger.info("Starting bot, please wait...")
            self.obs_client.connect()
            self.mods = self.host_service.get_moderators()
            self.subs = self.host_service.get_subscribers()
            with self.components_lock:
                for component in self.components.values():
                    self.__secure_component_method_call(component, "start")
            gLogger.info("Bot started")

        self.chat.start()
        self.chat.subscribe(self.handle_message)
        self.pubsub.start()
        self.pubsub.subscribe(self.handle_event)
        self.pubsub.listen(twitch.PubSubEvent.CHANNEL_POINTS)
        self.pubsub.listen(twitch.PubSubEvent.CHANNEL_SUBSCRIPTIONS)
        self.pubsub.listen(twitch.PubSubEvent.BITS)
        self.pubsub.listen(twitch.PubSubEvent.BITS_BADGE_NOTIFICATION)

    def stop(self):
        with self.start_stop_lock:
            gLogger.info("Stopping bot, please wait...")
            self.chat.stop()
            self.chat.join()
            self.pubsub.stop()
            self.pubsub.join()
            self.obs_client.disconnect()
            with self.components_lock:
                for component in self.components.values():
                    self.__secure_component_method_call(component, "stop")
                self.components.clear()
            self.is_running = False
            gLogger.info("Bot stopped")

    @staticmethod
    def __secure_component_method_call(component: ChatComponent, method_name: str, *args: Any, **kwargs: Any) -> bool:
        try:
            method = getattr(component, method_name)
            method(*args, **kwargs)
            return True
        except Exception as e:
            name = component.get_name()
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            gLogger.error(f"Error in component '{name}': {e}\n{traceback_str}")
        return False
