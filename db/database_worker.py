import sqlite3
from sqlite3 import DatabaseError, IntegrityError, ProgrammingError
from typing import Dict, List

default_path = "./db/image_store.db"


# A class for handling low-level database operations
class DatabaseWorker:
    # Construct this class and connect to the database
    def __init__(self, db_path: str, verbose: bool):
        self.db_path = db_path
        self.__db = sqlite3.connect(db_path)
        self.__cursor = self.__db.cursor()
        self.verbose = verbose

    # When finalizing this class, make sure to close the db cursor and connection
    def __del__(self):
        self.__cursor.close()
        self.__db.close()

    # Drop all databases created by this class
    def drop_dbs(self) -> None:
        print("Dropping metadata table")
        self.__cursor.execute("DROP TABLE IF EXISTS metadata ;", "")
        print("Dropping image table")
        self.__cursor.execute("DROP TABLE IF EXISTS image ;", "")
        print("Dropping image_ignore table")
        self.__cursor.execute("DROP TABLE IF EXISTS image_ignore ;", "")
        print("Dropping image_hashes table")
        self.__cursor.execute("DROP TABLE IF EXISTS image_hashes ;", "")

    # Execute a SQL query
    def execute(self, sql: str, bindings: Dict[str, any]):
        try:
            print(f"--- Executing sql statement ---\n{sql}\nwith bindings\n{str(bindings)}")
            self.__cursor.execute(sql, bindings)
        except (DatabaseError, IntegrityError, ProgrammingError) as e:
            raise Exception('Did not receive successful insert status for'
                            f' { {sql} }, message is { {str(e)} }', e)

    # Return the result of a query
    def get_result(self) -> List[any]:
        return self.__cursor.fetchall()

    # Get a single result from the query
    def get_single_result(self) -> List[any]:
        return self.__cursor.fetchone()

    # Commit changes to the db
    def commit_changes(self) -> None:
        self.__db.commit()

    # Rollback changes to the db
    def rollback_changes(self) -> None:
        self.__db.rollback()

    def get_warnings(self) -> List:
        return self.__cursor.fetchwarnings()

    def zip_object(self, obj: List[any], keys: List[str] = None) -> Dict[str, any]:
        if obj is None:
            return None
        if keys is None:
            keys = [col[0] for col in self.__cursor.description]
        return dict(zip(keys, obj))

    # Zip multiple results from a query (turn them into an object)
    def zip_objects(self, ls: List[any]) -> List[Dict[str, any]]:
        result = []
        for obj in ls:
            result.append(self.zip_object(obj))

        return result


