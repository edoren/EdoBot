import re

file_version_template = '''
# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=$FILE_VERSION_DATA$,
    prodvers=$PROD_VERSION_DATA$,
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=$FILE_FLAGS$,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x4,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [
            StringStruct(u'CompanyName', u'$PRODUCT_OWNER$'),
            StringStruct(u'FileDescription', u'$PRODUCT_FILE_DESCRIPTION$'),
            StringStruct(u'FileVersion', u'$PRODUCT_VERSION$'),
            StringStruct(u'InternalName', u'$PRODUCT_FILE_NAME$'),
            StringStruct(u'OriginalFilename', u'$PRODUCT_FILE_NAME$'),
            StringStruct(u'ProductName', u'$PRODUCT_NAME$'),
            StringStruct(u'ProductVersion', u'$PRODUCT_VERSION$'),
            StringStruct(u'Comments', u'$PRODUCT_DESCRIPTION$'),
            StringStruct(u'LegalCopyright', u'$PRODUCT_COPYRIGHT$')
        ])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''


VS_FF_DEBUG = 0x00000001
VS_FF_INFOINFERRED = 0x00000010
VS_FF_PATCHED = 0x00000004
VS_FF_PRERELEASE = 0x00000002
VS_FF_PRIVATEBUILD = 0x00000008
VS_FF_SPECIALBUILD = 0x00000020


def generate(output_path: str, name: str, owner: str, version: str,
             description: str = "", copyright: str = "", file_name: str = "",
             file_description: str = ""):
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
    file_contents = file_version_template
    found = set(re.findall(r"\$([a-zA-Z0-9-_]+)\$", file_contents, re.MULTILINE))
    all_keys_found = True
    for key in found:
        if key not in values:
            all_keys_found = False
            print(f"Error key '{key}' not found")
            continue
        file_contents = file_contents.replace(f"${key}$", values[key])
    if all_keys_found:
        with open(output_path, "w") as f:
            f.write(file_contents)
