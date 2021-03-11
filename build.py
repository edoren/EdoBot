import compileall
import os
import os.path
import re
import shutil
import subprocess
import sys
import PyInstaller

source_dir = os.path.dirname(__file__)
build_dir = os.path.join(source_dir, "build")

if not os.path.exists(build_dir):
    os.makedirs(build_dir)

os.chdir(source_dir)

python_exe = sys.executable

optimized = 2
if optimized == 0:
    optimized_flag = ""
    optimized_prefix = ""
else:
    optimized_flag = "-" + "O" * optimized
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
subprocess.run([
    python_exe,
    optimized_flag,
    "-m",
    "PyInstaller",
    "-F",
    # "--hidden-import=obswebsocket",
    os.path.join(source_dir, "src", "main.py")
])

print("======================== Copying data         ========================")

dest_dir = os.path.join(build_dir, "dist")
shutil.copytree(os.path.join(source_dir, "www"),
                os.path.join(dest_dir, "www"), dirs_exist_ok=True,
                copy_function=copy_function)
shutil.copytree(components_pycache,
                os.path.join(dest_dir, "components"), dirs_exist_ok=True,
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

module_dest_dir = os.path.join(dest_dir, "modules")
shutil.copytree(requirements_lib_folder, module_dest_dir,
                dirs_exist_ok=True, copy_function=copy_function,
                ignore=shutil.ignore_patterns("tests", "__pycache__",
                                              "*.dist-info", "*.py"))
