import json
import os.path
from typing import Any, List, Mapping, MutableMapping, Union

Path = List[Union[str, int]]

__all__ = ["Config"]


class Config:
    @staticmethod
    def __write_config(file: str, path: Path, data: Any) -> bool:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                f.write("{}")
        with open(file, "r") as f:
            config: MutableMapping = json.load(f)
        initial_config = config
        for key in path[:-1]:
            if isinstance(config, dict):
                if key not in config:
                    config[key] = {}
                config = config[key]
            else:
                return False
        config[path[-1]] = data
        with open(file, "w") as f:
            json.dump(initial_config, f, indent=4)
        return True

    @staticmethod
    def __read_config(file: str, path: Path) -> Any:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                f.write("{}")
        with open(file, "r") as f:
            config: Mapping = json.load(f)
        for key in path:
            if (isinstance(config, dict) and key in config) or \
                    (isinstance(config, list) and isinstance(key, int) and key < len(config)):
                config = config[key]
            else:
                return None
        return config

    def __init__(self, file: str, path: Path = []) -> None:
        self.file: str = file
        self.path: Path = path

    def __getitem__(self, key: Union[str, int]) -> "Config":
        return Config(self.file, self.path + [key])

    def get(self) -> Any:
        if len(self.path) > 0:
            return Config.__read_config(self.file, self.path)
        else:
            return None

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
