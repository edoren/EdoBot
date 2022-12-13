import os.path
from typing import Optional

from tinydb import TinyDB, where

from model import AccessToken

__all__ = ["DataBase"]


class DataBasePrivate:

    def __init__(self, store_dir):
        self.db = TinyDB(os.path.join(store_dir, "db.json"), indent=4)


class DataBase:
    instance: Optional[DataBasePrivate] = None

    def __init__(self, store_dir):
        if not DataBase.instance:
            DataBase.instance = DataBasePrivate(store_dir)
        self.__db = DataBase.instance.db

    def set_user_token(self, user: str, token: AccessToken) -> None:
        tokens_table = self.__db.table("tokens")
        findings = tokens_table.search(where("user") == user)
        if len(findings) == 0:
            tokens_table.insert({"user": user, "token": token.__dict__})
        else:
            tokens_table.update({"user": user, "token": token.__dict__}, where("user") == user)

    def get_token_for_user(self, user: str) -> Optional[AccessToken]:
        tokens_table = self.__db.table("tokens")
        findings = tokens_table.search(where("user") == user)
        if len(findings) > 0:
            return AccessToken(**findings[0]["token"])

    def remove_user(self, user: str) -> Optional[AccessToken]:
        tokens_table = self.__db.table("tokens")
        tokens_table.remove(where("user") == user)
