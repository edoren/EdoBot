import logging
import os
import os.path
import time
import traceback
from typing import List

import arrow

from core import Constants, EdoBot

gLogger = logging.getLogger(f"edobot.main")


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

    if not os.path.isdir(Constants.SAVE_DIRECTORY):
        os.makedirs(Constants.SAVE_DIRECTORY)

    config_file_path = os.path.join(Constants.SAVE_DIRECTORY, "config.json")

    if __debug__:
        print(f"Debug info: [PID: {os.getpid()}]")

    handlers: List[logging.Handler] = []
    format_txt = "%(threadName)s %(levelname)s %(name)s - %(message)s"

    file_handler = logging.FileHandler(os.path.join(Constants.SAVE_DIRECTORY, "out.log"), "a")
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
        bot = EdoBot()
        bot.run()
        components_folder = os.path.join(Constants.EXECUTABLE_DIRECTORY, "components")
        components = set()
        for file_name in os.listdir(components_folder):
            if os.path.isfile(os.path.join(components_folder, file_name)):
                components.add(os.path.splitext(file_name)[0])
        for name in components:
            bot.add_component(name)
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
