import sqlite3
import os
from sqlite3 import DatabaseError, IntegrityError, ProgrammingError

default_path = "./db/image_store.db"


class DatabaseWorker:
    def __init__(self, db_path, verbose):
        self.db_path = db_path
        self.__db = sqlite3.connect(db_path)
        self.__cursor = self.__db.cursor()
        self.verbose = verbose

    def __del__(self):
        self.__cursor.close()
        self.__db.close()

    def drop_dbs(self):
        print("Dropping metadata table")
        self.__cursor.execute("DROP TABLE IF EXISTS metadata ;", "")
        print("Dropping image table")
        self.__cursor.execute("DROP TABLE IF EXISTS image ;", "")
        print("Dropping image_ignore table")
        self.__cursor.execute("DROP TABLE IF EXISTS image_ignore ;", "")
        print("Dropping image_hashes table")
        self.__cursor.execute("DROP TABLE IF EXISTS image_hashes ;", "")

    def execute(self, sql, bindings):
        try:
            print(f"--- Executing sql statement ---\n{sql}\nwith bindings\n{str(bindings)}")
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

    def zip_object(self, obj, keys=None):
        # TODO fix this
        if keys is None:
            keys = self.__cursor.row()
        return dict(zip(keys, obj))

    def zip_objects(self, ls):
        keys = self.__cursor.row()
        result = []
        for obj in ls:
            result.append(self.zip_object(obj, keys=keys))

        return result


