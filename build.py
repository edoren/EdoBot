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

import PySide2.QtCore

import scripts.constants as constants  # type: ignore
from scripts.file_generator import generate_file_version_info, generate_nsis_file  # type: ignore

######################################################################

parser = argparse.ArgumentParser()
parser.add_argument("-O", "--optimized", help="Optimize the compiled python code", required=False, type=int, default=0,
                    choices=[0, 1, 2])
parser.add_argument("--output_dir", help="The folder to output the build", type=str, default="build")
parser.add_argument("--onefile", help="Generate a onefile executable", action="store_true")
parser.add_argument("--console", help="Create a console application", action="store_true")
parser.add_argument("--localization", "-l", help="Build only the localization files", action="store_true")
args = parser.parse_args()

######################################################################

source_dir = os.path.dirname(__file__)
data_dir = os.path.join(source_dir, "data")
build_dir = os.path.normpath(os.path.join(source_dir, args.output_dir))
components_dir = os.path.join(source_dir, "components")

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

if args.optimized:
    optimized_prefix = f".opt-{args.optimized}"
else:
    optimized_prefix = ""

py_cache_prefix = f".{sys.implementation.cache_tag}{optimized_prefix}.pyc"


def copy_function(src: str, dst: str):
    if dst.endswith(py_cache_prefix):
        dst = dst.replace(py_cache_prefix, ".pyc")
    logger.info('Copying {0}'.format(dst))
    shutil.copy2(src, dst)


logger.info("=================== Building localization files =====================")

pyside_dir = os.path.dirname(os.path.abspath(PySide2.QtCore.__file__))
lrelease_exe = os.path.join(pyside_dir, "lrelease.exe")

if os_name == "windows" and os.path.isfile(lrelease_exe):
    folders = [source_dir] + [
        os.path.join(components_dir, dI)
        for dI in os.listdir(components_dir) if os.path.isdir(os.path.join(components_dir, dI))
    ]
    files_to_process = []
    for folder in folders:
        for content in os.listdir(folder):
            content_path = os.path.join(folder, content)
            if content == "i18n" and os.path.isdir(content_path):
                for ts_file in os.listdir(content_path):
                    ts_file_path = os.path.join(content_path, ts_file)
                    if ts_file.endswith(".ts") and os.path.isfile(ts_file_path):
                        files_to_process.append(ts_file_path)
    result = subprocess.run([lrelease_exe] + files_to_process)

if args.localization:
    sys.exit(0)

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

internal_build_dir = os.path.join(build_dir, "build")
dist_dir = os.path.join(build_dir, "dist")
if os.path.exists(internal_build_dir):
    shutil.rmtree(internal_build_dir)
if os.path.exists(dist_dir):
    shutil.rmtree(dist_dir)

if not args.onefile:
    dist_dir = os.path.join(dist_dir, APP_NAME.lower())

os.chdir(build_dir)
pyinstaller_exec = [python_exe, "-m", "PyInstaller"]
pyinstaller_args: List[str] = []
hidden_imports: List[str] = constants.python_std_lib_list + ["PySide2.QtXml", "qtawesome"]
excluded_modules: List[str] = ["tkinter"]
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
if args.console:
    pyinstaller_args.append("--console")
else:
    pyinstaller_args.append("--windowed")
pyinstaller_args += [
    f"--name={APP_NAME.lower()}", f"--icon={APP_ICON}", "--noupx",
    os.path.join(source_dir, "src", "main.py")
]
my_env = os.environ.copy()
if args.optimized:
    my_env["PYTHONOPTIMIZE"] = str(args.optimized)
result = subprocess.run(pyinstaller_exec + pyinstaller_args, env=my_env)
if result.returncode != 0:
    sys.exit(result.returncode)

logger.info("=================== Copying data         ===================")

shutil.copytree(components_dir, os.path.join(dist_dir, "components"), dirs_exist_ok=True, copy_function=copy_function,
                ignore=shutil.ignore_patterns("__pycache__", "*.ts"))

shutil.copytree(os.path.join(source_dir, "i18n"), os.path.join(dist_dir, "i18n"), dirs_exist_ok=True,
                copy_function=copy_function, ignore=shutil.ignore_patterns("*.ts"))

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

bin_dir = os.path.join(build_dir, "bin")

if os.path.exists(bin_dir):
    shutil.rmtree(bin_dir)
os.makedirs(bin_dir)
os.chdir(bin_dir)

if os_name == "darwin":
    os_name = "macos"
arch = platform.architecture()[0]

file_name = f"{APP_NAME}-{version_str}-{os_name}-{arch}"
shutil.make_archive(file_name, 'zip', dist_dir, logger=logger)

if os_name == "windows":
    logger.info("================== Creating installer =====================")

    nsis_script_file = os.path.join(build_dir, "edobot.nsi")
    generate_nsis_file(nsis_script_file, APP_NAME, APP_OWNER, APP_EXECUTABLE, version_str, file_name, bin_dir, dist_dir)

    makensisw_exe = "C:\\Program Files (x86)\\NSIS\\makensis.exe"
    if os.path.isfile(makensisw_exe):
        subprocess.run([makensisw_exe, nsis_script_file])
    else:
        logger.error("NSIS not found make sure to install it")
