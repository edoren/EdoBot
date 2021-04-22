import compileall
import glob
import logging
import os
import os.path
import platform
import shutil
import subprocess
import sys
from typing import List

import scripts.file_version_info as file_version_info

source_dir = os.path.dirname(__file__)
data_dir = os.path.join(source_dir, "data")
build_dir = os.path.join(source_dir, "build")

os_name = platform.system().lower()

######################################################################

APP_NAME = "EdoBot"
APP_OWNER = "Edoren"
APP_ICON = os.path.join(data_dir, "icon.ico")
APP_DESCRIPTION = "Free and open source tool to create Twitch add chat interactions."
APP_COPYRIGHT = "(C) Manuel Sabogal"

######################################################################

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("edobot.build")

if not os.path.exists(build_dir):
    os.makedirs(build_dir)

os.chdir(source_dir)

python_exe = sys.executable

onefile = True
optimized = 2

# onefile has issues on Mac, maybe on linux too?
if platform.system() == "Darwin":
    onefile = False

if optimized == 0:
    optimized_prefix = ""
else:
    optimized_prefix = f".opt-{optimized}"

py_cache_prefix = f".{sys.implementation.cache_tag}{optimized_prefix}.pyc"


def copy_function(src: str, dst: str):
    if dst.endswith(py_cache_prefix):
        dst = dst.replace(py_cache_prefix, ".pyc")
    logger.info('Copying {0}'.format(dst))
    shutil.copy2(src, dst)


logger.info("=================== Collecting version =====================")

version_info_file = os.path.join(data_dir, "version.info")
logger.info(f"{version_info_file}")
with open(version_info_file, "w") as f:
    try:
        version_str = subprocess.check_output(["git", "describe", "--tags"]).decode("utf-8").strip()
    except Exception:
        version_str = "unknown"
    f.write(version_str)

file_version_info_path = os.path.join(build_dir, "file_version_info.txt")
file_version_info.generate(file_version_info_path, name=APP_NAME, owner=APP_OWNER, file_name=f"{APP_NAME.lower()}.exe",
                           file_description=APP_NAME, version=version_str, description=APP_DESCRIPTION,
                           copyright=APP_COPYRIGHT)

logger.info("=================== Creating executable  ===================")

os.chdir(build_dir)
pyinstaller_exec = [python_exe, "-m", "PyInstaller"]
pyinstaller_args: List[str] = []
hidden_imports: List[str] = ["uuid", "PySide2.QtXml"]
excluded_modules: List[str] = []
if not optimized:
    pyinstaller_args.append("--debug=noarchive")
    hidden_imports.append("xmlrpc.server")
    hidden_imports.append("site")
if onefile:
    pyinstaller_args.append("--onefile")
else:
    pyinstaller_args.append("--onedir")
for imp in hidden_imports:
    pyinstaller_args.append(f"--hidden-import={imp}")
for mod in excluded_modules:
    pyinstaller_args.append(f"--exclude-module={mod}")
for root, dire, files in os.walk(data_dir):
    relpath = os.path.relpath(root, data_dir)
    for fname in files:
        pyinstaller_args.append(f"--add-data={os.path.join(root, fname)}{os.pathsep}{os.path.join('data', relpath)}")
if os_name == "windows":
    pyinstaller_args.append(f"--version-file={file_version_info_path}")
pyinstaller_args += [
    f"--name={APP_NAME.lower()}",
    f"--icon={APP_ICON}",
    "--noconsole",
    "--windowed",
    "--noupx",
    os.path.join(source_dir, "src", "main.py")
]
my_env = os.environ.copy()
my_env["PYTHONOPTIMIZE"] = str(optimized)
result = subprocess.run(pyinstaller_exec + pyinstaller_args, env=my_env)
if result.returncode != 0:
    sys.exit(result.returncode)

logger.info("=================== Copying data         ===================")

components_dir = os.path.join(source_dir, "components")
dist_dir = os.path.join(build_dir, "dist")
if not onefile:
    dist_dir = os.path.join(dist_dir, APP_NAME)
shutil.copytree(components_dir,
                os.path.join(dist_dir, "components"), dirs_exist_ok=True,
                copy_function=copy_function,
                ignore=shutil.ignore_patterns("__pycache__"))
if not onefile:
    pass

logger.info("============== Downloading required modules ================")

additional_requirements: List[str] = []

pip_install_dir = os.path.join(build_dir, "pip")
if os.path.isdir(pip_install_dir):
    shutil.rmtree(pip_install_dir)
for requirement in additional_requirements:
    subprocess.run([python_exe, "-m", "pip", "install", "--ignore-installed",
                    f"--prefix={pip_install_dir}", requirement])

logger.info("================ Copying required modules ==================")

requirements_glob_pattern = os.path.join(pip_install_dir, "**", "site-packages")
requirements_lib_dirs = glob.glob(requirements_glob_pattern, recursive=True)
if len(requirements_lib_dirs) > 0:
    requirements_lib_dir = requirements_lib_dirs[0]
    compileall.compile_dir(requirements_lib_dir, legacy=True, optimize=optimized)
    module_dist_dir = os.path.join(dist_dir, "modules")
    shutil.copytree(requirements_lib_dir, module_dist_dir,
                    dirs_exist_ok=True, copy_function=copy_function,
                    ignore=shutil.ignore_patterns("tests", "__pycache__", "*.py",
                                                  "*.dist-info", "*.egg-info"))

logger.info("===================== Creating package =====================")

if os_name == "darwin":
    os_name == "macos"
arch = platform.architecture()[0]

zip_file_name = f"{APP_NAME}-{version_str}-{os_name}-{arch}"
shutil.make_archive(zip_file_name, 'zip', dist_dir, logger=logger)
