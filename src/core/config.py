import json
import logging
import os
import os.path
import traceback
from typing import Any, List, MutableMapping, Union

Path = List[Union[str, int]]
ConfigType = Union[MutableMapping[Union[str, int], Any], List[Any]]

__all__ = ["Config"]

gLogger = logging.getLogger(f"edobot.{__name__}")


class Config:
    @staticmethod
    def __create_if_not_exist(file_path: str) -> None:
        if not os.path.exists(file_path):
            file_dir = os.path.dirname(file_path)
            if not os.path.isdir(file_dir):
                os.makedirs(file_dir)
            with open(file_path, 'w', encoding="utf-8") as f:
                f.write("{}")
        elif os.stat(file_path).st_size == 0:
            with open(file_path, 'w', encoding="utf-8") as f:
                f.write("{}")

    @staticmethod
    def __write_config(file: str, path: Path, data: Any) -> bool:
        Config.__create_if_not_exist(file)
        with open(file, "r", encoding="utf-8") as f:
            initial_file_contents = f.read()
        config: ConfigType = json.loads(initial_file_contents)
        config_root = config
        for key in path[:-1]:
            if isinstance(config, dict):
                if key not in config:
                    config[key] = {}
                config = config[key]
            elif isinstance(config, list) and isinstance(key, int) and key < len(config):
                config = config[key]
            else:
                return False
        last_key = path[-1]
        if isinstance(config, dict):
            config[last_key] = data
        elif isinstance(config, list) and isinstance(last_key, int) and last_key < len(config):
            config[last_key] = data
        else:
            return False
        try:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(config_root, f, indent=4)
        except Exception as e:
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            gLogger.critical(f"Critical error: {e}\n{traceback_str}")
            with open(file, "w", encoding="utf-8") as f:
                f.write(initial_file_contents)
        return True

    @staticmethod
    def __read_config(file: str, path: Path) -> Any:
        Config.__create_if_not_exist(file)
        with open(file, "r", encoding="utf-8") as f:
            config: ConfigType = json.load(f)
        for key in path:
            if isinstance(config, dict) and key in config:
                config = config[key]
            elif isinstance(config, list) and isinstance(key, int) and key < len(config):
                config = config[key]
            else:
                return None
        return config

    def __init__(self, file: str, path: Path = []) -> None:
        self.file: str = file
        self.path: Path = path

    def __getitem__(self, key: Union[str, int]) -> "Config":
        return Config(self.file, self.path + [key])

    def get(self, default: Any = None) -> Any:
        if len(self.path) > 0:
            ret = Config.__read_config(self.file, self.path)
            if ret is not None:
                return ret
        return default

    def setdefault(self, default: Any = None) -> Any:
        if len(self.path) > 0:
            ret = Config.__read_config(self.file, self.path)
            if ret is not None:
                return ret
        Config.__write_config(self.file, self.path, default)
        return default

    def __invert__(self) -> Any:
        return self.get()

    def __str__(self) -> str:
        return str(self.get())

    def __setitem__(self, key: Union[str, int], data: Any) -> bool:
        return Config(self.file, self.path + [key]).set(data)

    def set(self, data: Any) -> bool:
        if len(self.path) > 0:
            return Config.__write_config(self.file, self.path, data)
        else:
            return False
