from db.database import DatabaseWorker, default_path


class DatabaseImageHandler:
    def __init__(self, db_path, db_timeout):
        self.worker = DatabaseWorker(db_path, db_timeout)

    def find_image(self, md5):
        self.worker.execute(
            "SELECT name, a_hash, p_hash, d_hash, reduced_image_size FROM image WHERE md5_hash = :hash_val;",
            {"hash_val": md5})
        return self.worker.get_single_result()

    def save_image(self, md5, a_hash, d_hash, p_hash, name,
                   reduced_image_size, width, height):
        self.worker.execute("INSERT INTO image (md5_hash, a_hash, d_hash, p_hash, name, "
                            "reduced_image_size, width, height)"
                            "VALUES (:md5, :a_hash, :d_hash, :p_hash, "
                            ":name, :size, :width, :height);",
                            {"md5": md5, "a_hash": a_hash, "d_hash": d_hash, "p_hash": p_hash, "name": name,
                             "size": reduced_image_size, "width": width, "height": height})
