import sqlite3
import os
from sqlite3 import DatabaseError, IntegrityError, ProgrammingError

default_path = "./db/image_store.db"


class DatabaseWorker:
    def __init__(self, db_path, db_timeout=5):
        self.db_path = db_path
        self.__db = sqlite3.connect(db_path, timeout=db_timeout)
        self.__cursor = self.__db.cursor()

    def __del__(self):
        self.__cursor.close()
        self.__db.close()

    def drop_db(self):
        self.__cursor.execute("DROP TABLE IF EXISTS metadata ;", "")
        self.__cursor.execute("DROP TABLE IF EXISTS image ;", "")

    def execute(self, sql, bindings):
        try:
            self.__cursor.execute(sql, bindings)
        except (DatabaseError, IntegrityError, ProgrammingError) as e:
            raise Exception('Did not receive successful insert status for'
                            f' { {sql} }, message is { {str(e)} }')

    def get_result(self):
        return self.__cursor.fetchall()

    def get_single_result(self):
        return self.__cursor.fetchone()

    def commit_changes(self):
        self.__db.commit()

    def rollback_changes(self):
        self.__db.rollback()
