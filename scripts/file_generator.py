import os.path
import re
from typing import Mapping

VS_FF_DEBUG = 0x00000001
VS_FF_INFOINFERRED = 0x00000010
VS_FF_PATCHED = 0x00000004
VS_FF_PRERELEASE = 0x00000002
VS_FF_PRIVATEBUILD = 0x00000008
VS_FF_SPECIALBUILD = 0x00000020


def __configure_file(output_file: str, input_str: str, data: Mapping[str, str], delimiter: str = "$"):
    contents = input_str
    found = set(re.findall(f"\\{delimiter}([a-zA-Z0-9-_]+)\\{delimiter}", contents, re.MULTILINE))
    all_keys_found = True
    for key in found:
        if key not in data:
            all_keys_found = False
            print(f"Error key '{key}' not found")
            continue
        contents = contents.replace(f"{delimiter}{key}{delimiter}", data[key])
    if all_keys_found:
        with open(output_file, "w") as f:
            f.write(contents)


def generate_file_version_info(output_path: str, name: str, owner: str, version: str, description: str = "",
                               copyright: str = "", file_name: str = "", file_description: str = ""):
    current_dir = os.path.dirname(__file__)
    file_version_template_file = os.path.join(current_dir, "input", "file_version_info.txt.in")
    with open(file_version_template_file, "r") as f:
        file_version_template = f.read()

    values: dict[str, str] = {
        "PRODUCT_NAME": name,
        "PRODUCT_OWNER": owner,
        "PRODUCT_VERSION": version,
        "PRODUCT_FILE_NAME": file_name if file_name else f"{name.lower()}.exe",
        "PRODUCT_FILE_DESCRIPTION": file_description if file_description else name,
        "PRODUCT_DESCRIPTION": description,
        "PRODUCT_COPYRIGHT": copyright
    }

    semver_regex = r"^([0-9]+)\.([0-9]+)\.([0-9]+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+)?$"
    semver_matches = re.findall(semver_regex, version)
    if len(semver_matches) == 1:
        semver = semver_matches[0]
        major_version = int(semver[0])
        minor_version = int(semver[1])
        patch_version = int(semver[2])
        metadata = semver[3]
        if metadata and metadata.startswith(("beta", "alpha", "rc")):
            values["FILE_FLAGS"] = hex(VS_FF_PRERELEASE)
        version_tuple = (major_version, minor_version, patch_version, 0)
        values["FILE_VERSION_DATA"] = str(version_tuple)
        values["PROD_VERSION_DATA"] = str(version_tuple)
    else:
        values["FILE_FLAGS"] = str("0x0")

    __configure_file(output_path, file_version_template, values)


def generate_nsis_file(output_path: str, app_name: str, app_owner: str, app_executable: str, app_version: str,
                       installer_name: str, dist_folder: str):
    current_dir = os.path.dirname(__file__)
    nsis_script_template_file = os.path.join(current_dir, "input", "edobot.nsi.in")
    with open(nsis_script_template_file, "r") as f:
        nsis_script_template = f.read()

    values: dict[str, str] = {
        "APP_NAME": app_name,
        "APP_OWNER": app_owner,
        "APP_EXECUTABLE": app_executable,
        "APP_VERSION": app_version,
        "OUTPUT_INSTALLER_NAME": installer_name,
        "DIST_FOLDER": dist_folder
    }

    __configure_file(output_path, nsis_script_template, values, "%")
