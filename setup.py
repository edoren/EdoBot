from setuptools import setup

with open("requirements.txt", "r", encoding="utf-8") as req_file:
    install_requires = [req for req in req_file.readlines() if len(req.strip()) > 0]

setup(name="edobot", version="1.0.0", install_requires=install_requires)
