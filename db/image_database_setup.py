from . import database

database_version = 0.1


def check_db_version(db_path, db_timeout):
    worker = database.DatabaseWorker(db_path=db_path, db_timeout=db_timeout)
    worker.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name=:table_name ;",
                   {"table_name": "metadata"})

    row = worker.get_single_result()
    correct_version = True
    if row is None:
        correct_version = False
    else:
        worker.execute("SELECT version FROM metadata ;", "")
        row = worker.get_single_result()
        if row is None or row[0] != database:
            correct_version = False

    if correct_version:
        return

    worker.drop_db()
    recreate_db(db_path, db_timeout)


def recreate_db(db_path, db_timeout):
    worker = database.DatabaseWorker(db_path=db_path, db_timeout=db_timeout)
    worker.execute("CREATE TABLE metadata ("
                   "version REAL"
                   ") ;", "")
    worker.execute("INSERT INTO metadata VALUES (:version) ;", {"version": database_version})

    worker.execute("CREATE TABLE image ("
                   "md5_hash TEXT NOT NULL UNIQUE,"
                   "p_hash TEXT NOT NULL,"
                   "a_hash TEXT NOT NULL,"
                   "d_hash TEXT NOT NULL,"
                   "name TEXT NOT NULL,"
                   "reduced_image_size INTEGER NOT NULL,"
                   "created DATETIME DEFAULT CURRENT_TIMESTAMP,"
                   "width INTEGER,"
                   "height INTEGER"
                   ") ;", "")

    worker.commit_changes()
