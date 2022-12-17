import argparse
import os
import os.path
import platform
import subprocess
import sys

import PySide6.QtCore

######################################################################

parser = argparse.ArgumentParser()
parser.add_argument("--components", "-c", help="Components folder to update", nargs='+', type=str)
args = parser.parse_args()

######################################################################

source_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

src_dir = os.path.join(source_dir, "src")
data_dir = os.path.join(source_dir, "data")
i18n_dir = os.path.join(source_dir, "i18n")

os_name = platform.system().lower()

######################################################################

languages = ["en", "es"]

lupdate_exe = None

if os_name == "windows":
    pyside_dir = os.path.dirname(os.path.abspath(PySide6.QtCore.__file__))
    lupdate_path = os.path.join(pyside_dir, "lupdate.exe")
    if os.path.isfile(lupdate_path):
        lupdate_exe = lupdate_path

if lupdate_exe is None:
    print("lupdate not found")
    sys.exit()

result = None

if args.components is None:
    dirs_to_check = [os.path.join(data_dir, "designer"), os.path.join(src_dir, "gui")]
    language_files = [os.path.join(i18n_dir, "{}.ts".format(lang)) for lang in languages]
    result = subprocess.run([lupdate_exe, "-extensions", "ui,py"] + dirs_to_check + ["-ts"] + language_files)
else:
    print(args.components)
    for comp in args.components:
        if not os.path.isdir(comp):
            print("Error invalid component '{}'".format(comp))
            continue

        i18n_comp_dir = os.path.join(comp, "i18n")
        if not os.path.isdir(i18n_comp_dir):
            os.makedirs(i18n_comp_dir)

        language_files = [os.path.join(i18n_comp_dir, "{}.ts".format(lang)) for lang in languages]
        result = subprocess.run([lupdate_exe, "-extensions", "ui,py", comp, "-ts"] + language_files)
