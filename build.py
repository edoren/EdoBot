import argparse
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

import scripts.constants as constants  # type: ignore
from scripts.file_generator import generate_file_version_info, generate_nsis_file  # type: ignore

source_dir = os.path.dirname(__file__)
data_dir = os.path.join(source_dir, "data")
build_dir = os.path.join(source_dir, "build")

os_name = platform.system().lower()

######################################################################

APP_NAME = "EdoBot"
APP_OWNER = "Edoren"
APP_EXECUTABLE = f"{APP_NAME.lower()}"
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

parser = argparse.ArgumentParser()
parser.add_argument("-O", "--optimized", help="Optimize the compiled python code", required=False, type=int, default=0,
                    choices=[0, 1, 2])
parser.add_argument("--onefile", help="Generate a onefile executable", action="store_true")
args = parser.parse_args()

if args.optimized:
    optimized_prefix = ""
else:
    optimized_prefix = f".opt-{args.optimized}"

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
generate_file_version_info(file_version_info_path, name=APP_NAME, owner=APP_OWNER, file_name=f"{APP_EXECUTABLE}.exe",
                           file_description=APP_NAME, version=version_str, description=APP_DESCRIPTION,
                           copyright=APP_COPYRIGHT)

logger.info("=================== Creating executable  ===================")

os.chdir(build_dir)
pyinstaller_exec = [python_exe, "-m", "PyInstaller"]
pyinstaller_args: List[str] = []
hidden_imports: List[str] = constants.python_std_lib_list + ["PySide2.QtXml"]
excluded_modules: List[str] = []
if not args.optimized:
    pyinstaller_args.append("--debug=noarchive")
    hidden_imports.append("xmlrpc.server")
    hidden_imports.append("site")
if args.onefile:
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
    f"--name={APP_NAME.lower()}", f"--icon={APP_ICON}", "--noconsole", "--windowed", "--noupx",
    os.path.join(source_dir, "src", "main.py")
]
my_env = os.environ.copy()
my_env["PYTHONOPTIMIZE"] = str(args.optimized)
result = subprocess.run(pyinstaller_exec + pyinstaller_args, env=my_env)
if result.returncode != 0:
    sys.exit(result.returncode)

logger.info("=================== Copying data         ===================")

components_dir = os.path.join(source_dir, "components")
dist_dir = os.path.join(build_dir, "dist")
if not args.onefile:
    dist_dir = os.path.join(dist_dir, APP_NAME)
shutil.copytree(components_dir, os.path.join(dist_dir, "components"), dirs_exist_ok=True, copy_function=copy_function,
                ignore=shutil.ignore_patterns("__pycache__"))

logger.info("============== Downloading required modules ================")

additional_requirements: List[str] = []

pip_install_dir = os.path.join(build_dir, "pip")
if os.path.isdir(pip_install_dir):
    shutil.rmtree(pip_install_dir)
for requirement in additional_requirements:
    subprocess.run(
        [python_exe, "-m", "pip", "install", "--ignore-installed", f"--prefix={pip_install_dir}", requirement])

logger.info("================ Copying required modules ==================")

requirements_glob_pattern = os.path.join(pip_install_dir, "**", "site-packages")
requirements_lib_dirs = glob.glob(requirements_glob_pattern, recursive=True)
if len(requirements_lib_dirs) > 0:
    requirements_lib_dir = requirements_lib_dirs[0]
    compileall.compile_dir(requirements_lib_dir, legacy=True, optimize=args.optimized)
    module_dist_dir = os.path.join(dist_dir, "modules")
    shutil.copytree(requirements_lib_dir, module_dist_dir, dirs_exist_ok=True, copy_function=copy_function,
                    ignore=shutil.ignore_patterns("tests", "__pycache__", "*.py", "*.dist-info", "*.egg-info"))

logger.info("================= Creating zip package =====================")

if os_name == "darwin":
    os_name = "macos"
arch = platform.architecture()[0]

zip_file_name = f"{APP_NAME}-{version_str}-{os_name}-{arch}"
shutil.make_archive(zip_file_name, 'zip', dist_dir, logger=logger)

if os_name == "windows" and args.onefile:
    logger.info("================== Creating installer =====================")

    nsis_script_file = os.path.join(build_dir, "edobot.nsi")
    estimated_size = sum(os.path.getsize(f) for f in os.listdir(dist_dir) if os.path.isfile(f))
    generate_nsis_file(nsis_script_file, APP_NAME, APP_OWNER, APP_EXECUTABLE, version_str, zip_file_name, dist_dir)

    makensisw_exe = "C:\\Program Files (x86)\\NSIS\\makensis.exe"
    if os.path.isfile(makensisw_exe):
        subprocess.run([makensisw_exe, nsis_script_file])
    else:
        logger.error("NSIS not found make sure to install it")
