import os
import os.path
import platform
import sys
from typing import Final

__all__ = ["Constants"]

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _exe_dir = os.path.dirname(sys.executable)
    sys.path.append(os.path.join(_exe_dir, "modules"))
else:
    _exe_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

if platform.system() == "Windows":
    _save_dir = os.path.join(os.environ["APPDATA"], "EdoBot")
elif platform.system() in ["Linux", "Darwin"]:
    _save_dir = os.path.join(os.environ["HOME"], ".edobot")
else:
    print(f"Platform '{platform.system()}' not supported")
    sys.exit(-1)


class Constants:
    CLIENT_ID: Final[str] = "w2bmwjuyuxyz7hmz5tjpjorlerkn9u"
    EXECUTABLE_DIRECTORY: Final[str] = _exe_dir
    SAVE_DIRECTORY: Final[str] = _save_dir
