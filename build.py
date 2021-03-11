import compileall
import os
import os.path
import shutil
import subprocess
import sys

source_dir = os.path.dirname(__file__)
build_dir = os.path.join(source_dir, "build")

######################################################################

APP_NAME = "edobot"
APP_ICON = os.path.join(source_dir, "www", "favicon.ico")

######################################################################


if not os.path.exists(build_dir):
    os.makedirs(build_dir)

os.chdir(source_dir)

python_exe = sys.executable

optimized = 0
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
subprocess.run(
    pyinstaller_exec + [f"--hidden-import={x}" for x in hidden_imports] +
    ["-F", f"--name={APP_NAME}",  f"--icon={APP_ICON}",
     os.path.join(source_dir, "src", "main.py")]
)

print("======================== Copying data         ========================")

dist_dir = os.path.join(build_dir, "dist")
shutil.copytree(os.path.join(source_dir, "www"),
                os.path.join(dist_dir, "www"), dirs_exist_ok=True,
                copy_function=copy_function)
shutil.copytree(components_pycache,
                os.path.join(dist_dir, "components"), dirs_exist_ok=True,
                copy_function=copy_function,
                ignore=shutil.ignore_patterns("*.py"))

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

requirements_lib_folder = os.path.join(pip_install_dir, "Lib", "site-packages")
compileall.compile_dir(requirements_lib_folder, legacy=True, optimize=optimized)

module_dist_dir = os.path.join(dist_dir, "modules")
shutil.copytree(requirements_lib_folder, module_dist_dir,
                dirs_exist_ok=True, copy_function=copy_function,
                ignore=shutil.ignore_patterns("tests", "__pycache__",
                                              "*.dist-info", "*.py"))

shutil.make_archive(APP_NAME, 'zip', dist_dir)
