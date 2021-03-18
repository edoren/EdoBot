import getpass
import importlib
import importlib.util
import inspect
import logging
import os
import os.path
import sys
import threading
import time
import traceback
from typing import List, MutableMapping, Set

import arrow

import twitch
from core import App, ChatComponent, Config, UserType
from core.obswrapper import OBSWrapper
from twitch.pubsub import PubSub

gLogger = logging.getLogger(f"edobot.main")


class EdoBot:
    def __init__(self, config_file_path: str):
        self.config = Config(config_file_path)
        self.components: MutableMapping[str, ChatComponent] = {}
        self.start_stop_lock = threading.Lock()

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

        components_config = self.config["components"]

        components_folder = os.path.join(App.EXECUTABLE_DIRECTORY, "components")
        if not os.path.isdir(components_folder):
            return

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
                if issubclass(class_type, ChatComponent) and class_type is not ChatComponent:
                    component_name = class_type.get_name()
                    if component_name not in ~components_config:
                        components_config[component_name] = {}
                    gLogger.info(f"Adding component '{component_name}' with class name '{name}'")
                    class_instance = class_type()  # type: ignore
                    class_instance.config_component(config=components_config[component_name],
                                                    obs_client=self.obs_client.get_client())
                    self.components[component_name] = class_instance

            self.is_running = False

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
        for name, component in self.components.items():
            try:
                comp_command = component.get_command()
                if is_command:
                    command_pack = text.lstrip("!").split(" ", 1)
                    command = command_pack[0]
                    message = command_pack[1] if len(command_pack) > 1 else ""
                    if ((isinstance(comp_command, str) and command == comp_command) or
                            (isinstance(comp_command, list) and command in comp_command)):
                        component.process_message(message, user, user_types)
                elif comp_command is None:
                    component.process_message(text, user, user_types)
            except Exception as e:
                traceback_str = ''.join(traceback.format_tb(e.__traceback__))
                gLogger.error(f"Error in component '{name}': {e}\n{traceback_str}")
                # TODO: POP ITEMS

    def handle_event(self, topic: str, data: PubSub.EventTypes):
        # for component in self.components.values():
        #     component.process_event(topic, data["data"])
        print(topic, data)
        pass

    def run(self):
        if self.is_running:
            gLogger.info("Bot already started, stop it first")
            return

        with self.start_stop_lock:
            gLogger.info("Starting bot, please wait...")
            self.obs_client.connect()
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

        self.is_running = True

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
            for name, component in self.components.items():
                try:
                    component.stop()
                except Exception as e:
                    traceback_str = ''.join(traceback.format_tb(e.__traceback__))
                    gLogger.error(f"Error in component '{name}': {e}\n{traceback_str}")
            gLogger.info("Bot stopped")


class TimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        locale = arrow.now()
        if datefmt:
            return locale.format(datefmt)
        else:
            return locale.isoformat(timespec="seconds")


if __name__ == "__main__":
    print("------------------------------------------------------------")
    print("------------------------ EdoBot 1.0 ------------------------")
    print("------------------------------------------------------------", flush=True)

    if not os.path.isdir(App.SAVE_DIRECTORY):
        os.makedirs(App.SAVE_DIRECTORY)

    config_file_path = os.path.join(App.SAVE_DIRECTORY, "config.json")

    if __debug__:
        print(f"Debug info: [PID: {os.getpid()}]")

    handlers: List[logging.Handler] = []
    format_txt = "%(threadName)s %(levelname)s %(name)s - %(message)s"

    file_handler = logging.FileHandler(os.path.join(App.SAVE_DIRECTORY, "out.log"), "a")
    file_handler.setLevel(logging.NOTSET)
    file_handler.setFormatter(TimeFormatter("[%(asctime)s] %(process)s " + format_txt))
    handlers.append(file_handler)

    stream_handler = logging.StreamHandler(None)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(TimeFormatter(format_txt))
    handlers.append(stream_handler)

    logging.basicConfig(level=logging.NOTSET, handlers=handlers)

    bot = None
    try:
        bot = EdoBot(config_file_path)

        # def signal_handler(sig, frame):
        #     if sig == signal.SIGINT:
        #         if os.name != "posix":
        #             print("^C")
        #         if bot is not None:
        #             bot.stop()
        #             bot = None

        # signal.signal(signal.SIGINT, signal_handler)
        bot.run()
        while True:
            time.sleep(1000)
    except SyntaxError as e:
        raise e
    except KeyboardInterrupt:
        if os.name != "posix":
            print("^C")
    except Exception as e:
        traceback_str = ''.join(traceback.format_tb(e.__traceback__))
        gLogger.critical(f"Critical error: {e}\n{traceback_str}")
    finally:
        if bot is not None:
            bot.stop()
            bot = None
