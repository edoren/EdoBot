import compileall
import glob
import os
import os.path
import platform
import shutil
import subprocess
import sys

source_dir = os.path.dirname(__file__)
data_dir = os.path.join(source_dir, "data")
build_dir = os.path.join(source_dir, "build")

######################################################################

APP_NAME = "edobot"
APP_ICON = os.path.join(data_dir, "icon.ico")

######################################################################

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


def copy_function(src, dst):
    if dst.endswith(py_cache_prefix):
        dst = dst.replace(py_cache_prefix, ".pyc")
    print('Copying {0}'.format(dst))
    shutil.copy2(src, dst)


print("======================== Compiling components ========================")

components_dir = os.path.join(source_dir, "components")
components_pycache = os.path.join(components_dir, "__pycache__")
if os.path.isdir(components_pycache):
    shutil.rmtree(components_pycache)
compileall.compile_dir(components_dir, optimize=optimized)

print("======================== Creating executable  ========================")

os.chdir(build_dir)
pyinstaller_exec = [python_exe, "-m", "PyInstaller"]
hidden_imports = []
if optimized:
    pyinstaller_exec.insert(1, "-" + "O" * optimized)
else:
    # pyinstaller_exec.append("--debug=bootloader")
    pyinstaller_exec.append("--debug=noarchive")
    hidden_imports.append("xmlrpc.server")
    hidden_imports.append("site")
if onefile:
    pyinstaller_exec.append("--onefile")
for imp in hidden_imports:
    pyinstaller_exec.append(f"--hidden-import={imp}")
subprocess.run(
    pyinstaller_exec +
    [f"--name={APP_NAME}",  f"--icon={APP_ICON}",
     os.path.join(source_dir, "src", "main.py")]
)

print("======================== Copying data         ========================")

dist_dir = os.path.join(build_dir, "dist")
if not onefile:
    dist_dir = os.path.join(dist_dir, APP_NAME)
shutil.copytree(os.path.join(source_dir, "www"),
                os.path.join(dist_dir, "www"), dirs_exist_ok=True,
                copy_function=copy_function)
shutil.copytree(components_pycache,
                os.path.join(dist_dir, "components"), dirs_exist_ok=True,
                copy_function=copy_function,
                ignore=shutil.ignore_patterns("*.py"))
if not onefile:
    pass

print("=================== Downloading required modules =====================")

additional_requirements = [
    "obs-websocket-py==0.5.3"
]

pip_install_dir = os.path.join(build_dir, "pip")
if os.path.isdir(pip_install_dir):
    shutil.rmtree(pip_install_dir)
for requirement in additional_requirements:
    subprocess.run([python_exe, "-m", "pip", "install", "--ignore-installed",
                    f"--prefix={pip_install_dir}", requirement])

print("===================== Copying required modules =======================")

requirements_glob_pattern = os.path.join(pip_install_dir, "**", "site-packages")
requirements_lib_dir = glob.glob(requirements_glob_pattern, recursive=True)[0]
compileall.compile_dir(requirements_lib_dir, legacy=True, optimize=optimized)

module_dist_dir = os.path.join(dist_dir, "modules")
shutil.copytree(requirements_lib_dir, module_dist_dir,
                dirs_exist_ok=True, copy_function=copy_function,
                ignore=shutil.ignore_patterns("tests", "__pycache__", "*.py",
                                              "*.dist-info", "*.egg-info"))

shutil.make_archive(APP_NAME, 'zip', dist_dir)
