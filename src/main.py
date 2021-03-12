import importlib
import importlib.util
import inspect
import logging
import os
import os.path
import signal
import sys
import threading
import traceback
from typing import MutableMapping, Optional, Set

import twitch
from core import App, ChatComponent, Config, UserType

gLogger = logging.getLogger("me.edoren.edobot.main")


class TwitchChat:
    def __init__(self, config_file_path: str):
        self.irc: Optional[twitch.IRC] = None
        self.config = Config(config_file_path)
        self.components: MutableMapping[str, ChatComponent] = {}
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
            self.host_service = twitch.Service(account_login, scope)
            self.bot_service = self.host_service
        else:
            self.host_service = twitch.Service(account_login, host_scope)
            self.bot_service = twitch.Service(bot_account_login, bot_scope)

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
                    self.components[component_name] = class_type(components_config[component_name])

    def handle_message(self, data: bytes) -> None:
        text = data.decode("UTF-8").strip('\n\r')
        if text.find('PRIVMSG') < 0:
            return

        message_sender = text.split('!', 1)[0][1:]
        message_text = text.split('PRIVMSG', 1)[1].split(':', 1)[1]

        user_types: Set[UserType] = {UserType.CHATTER}

        if self.host_service.user.login == message_sender:
            user_types.add(UserType.BROADCASTER)
            user_types.add(UserType.MODERATOR)
            user_types.add(UserType.SUBSCRIPTOR)
            user_types.add(UserType.VIP)

        for user in self.mods:
            if user.user_login == message_sender:
                user_types.add(UserType.MODERATOR)

        for user in self.subs:
            if user.user_login == message_sender:
                user_types.add(UserType.SUBSCRIPTOR)

        user = self.host_service.get_users([message_sender])[0]

        is_command = message_text.startswith("!")
        for name, component in self.components.items():
            try:
                comp_command = component.get_command()
                if is_command:
                    command_pack = message_text.lstrip("!").split(" ", 1)
                    command = command_pack[0]
                    message = command_pack[1] if len(command_pack) > 1 else ""
                    if ((isinstance(comp_command, str) and command == comp_command) or
                            (isinstance(comp_command, list) and command in comp_command)):
                        component.process_message(message, user, user_types)
                elif comp_command is None:
                    component.process_message(message_text, user, user_types)
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
            self.irc = twitch.IRC(self.bot_service.user.display_name, self.bot_service.token.access_token)
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
    print("------------------------------------------------------------")
    print("------------------------ EdoBot 1.0 ------------------------")
    print("------------------------------------------------------------", flush=True)

    if not os.path.isdir(App.SAVE_DIRECTORY):
        os.makedirs(App.SAVE_DIRECTORY)

    config_file_path = os.path.join(App.SAVE_DIRECTORY, "config.json")

    if __debug__:
        print(f"Debug info: [PID: {os.getpid()}]")

    handlers = []
    format_txt = "%(threadName)s %(levelname)s %(name)s - %(message)s"

    file_handler = logging.FileHandler(os.path.join(App.SAVE_DIRECTORY, "out.log"), "a")
    file_handler.setLevel(logging.NOTSET)
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(process)s " + format_txt, "%Y-%m-%d %H:%M:%S %z"))
    handlers.append(file_handler)

    stream_handler = logging.StreamHandler(None)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(format_txt))
    handlers.append(stream_handler)

    logging.basicConfig(level=logging.NOTSET, handlers=handlers)

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
