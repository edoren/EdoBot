import os
import os.path
import platform
import sys
import tempfile
from typing import Final

__all__ = ["Constants"]

_app_name = "EdoBot"

_is_frozen = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
if _is_frozen:
    _exe_dir = os.path.dirname(sys.executable)
    _data_dir = os.path.join(sys._MEIPASS, "data")  # type: ignore
    sys.path.append(os.path.join(_exe_dir, "modules"))
    with open(os.path.join(_data_dir, "version.info"), "r") as f:
        _app_version = f.read()
else:
    _exe_dir = os.path.normpath(os.getcwd())
    _data_dir = os.path.join(_exe_dir, "data")
    _app_version = "unknown"
    if __debug__:
        import subprocess

        try:
            _app_version = subprocess.check_output(["git", "describe", "--tags"]).decode("utf-8").strip()
            _app_version += "-"
            _app_version += subprocess.check_output(["git", "branch", "--show-current"]).decode("utf-8").strip()
        except Exception:
            pass

if platform.system() == "Windows":
    _save_dir = os.path.join(os.environ["APPDATA"], _app_name)
elif platform.system() in ["Linux", "Darwin"]:
    _save_dir = os.path.join(os.environ["HOME"], f".{_app_name.lower()}")
else:
    print(f"Platform '{platform.system()}' not supported")
    sys.exit(-1)


class Constants:
    IS_FROZEN: Final[bool] = _is_frozen
    APP_NAME: Final[str] = _app_name
    APP_VERSION: Final[str] = _app_version
    CLIENT_ID: Final[str] = "w2bmwjuyuxyz7hmz5tjpjorlerkn9u"
    EXECUTABLE_DIRECTORY: Final[str] = _exe_dir
    SAVE_DIRECTORY: Final[str] = _save_dir
    DATA_DIRECTORY: Final[str] = _data_dir
    TMP_DIRECTORY: Final[str] = os.path.join(tempfile.gettempdir(), _app_name)
    CONFIG_DIRECTORY: Final[str] = os.path.join(_save_dir, "config")
