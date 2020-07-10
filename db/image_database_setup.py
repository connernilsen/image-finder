from . import database

database_version = 0.1
migrations = [
    (0.1, "CREATE TABLE image ("
          "md5_hash TEXT NOT NULL UNIQUE,"
          "name TEXT NOT NULL,"
          "created DATETIME DEFAULT CURRENT_TIMESTAMP,"
          "width INTEGER,"
          "height INTEGER,"
          "CONSTRAINT image_pk "
          "PRIMARY KEY (md5_hash)"
          ") ;"
     ),
    (0.2, "CREATE TABLE image_ignore ("
          "md5_hash_1 TEXT NOT NULL, "
          "md5_hash_2 TEXT NOT NULL, "
          "created DATETIME DEFAULT CURRENT_TIMESTAMP, "
          "CONSTRAINT image_ignore_pk "
          "PRIMARY KEY (md5_hash_1, md5_hash_2) " # ", "
          # "CONSTRAINT image_ignore_md5_1 "
          # "(md5_hash_1) FOREIGN KEY image (md5_hash), "
          # "CONSTRAINT image_ignore_md5_2 "
          # "(md5_hash_2) FOREIGN KEY image (md5_hash)"
          ") ;"
     ),
    (0.3, "CREATE TABLE image_hashes ( "
          "md5_hash TEXT NOT NULL, "
          "p_hash TEXT NOT NULL, "
          "a_hash TEXT NOT NULL, "
          "d_hash TEXT NOT NULL, "
          "reduced_size_factor INTEGER NOT NULL, "
          "CONSTRAINT image_hashes_pk "
          "PRIMARY KEY (md5_hash, reduced_size_factor)"
          ") ;"
     )
]


def check_db_version(db_path, verbose):
    worker = database.DatabaseWorker(db_path, verbose)
    if verbose:
        print("Checking db version")
    worker.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name=:table_name ;",
                   {"table_name": "metadata"})

    row = worker.get_single_result()
    correct_version = True
    current_version = database_version
    if row is None:
        correct_version = False
        current_version = 0
    else:
        worker.execute("SELECT version FROM metadata ;", "")
        row = worker.get_single_result()
        if row is None:
            correct_version = False
            current_version = 0
        elif row[0] < database_version:
            correct_version = False
            current_version = row[0]

    if correct_version:
        if verbose:
            print("Correct version found")
        return

    if verbose:
        print("Updating db")
    update_db(db_path, current_version, verbose)


def update_db(db_path, current_version, verbose):
    worker = database.DatabaseWorker(db_path, verbose)
    worker.execute("CREATE TABLE metadata ("
                   "version REAL"
                   ") ;", "")
    worker.execute("INSERT INTO metadata VALUES (:version) ;", {"version": database_version})

    i = 0
    for migration in migrations:
        if current_version < migration[0]:
            break
        i += 1

    for migration in migrations[i:]:
        worker.execute(migration[1], "")

    worker.commit_changes()


def drop_db(db_path, verbose):
    if verbose:
        print("Dropping dbs")
    worker = database.DatabaseWorker(db_path, verbose)
    worker.drop_dbs()
