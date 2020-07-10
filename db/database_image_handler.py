from db.database import DatabaseWorker, default_path


class DatabaseImageHandler:
    def __init__(self, db_path, verbose):
        self.worker = DatabaseWorker(db_path, verbose)

    def find_image(self, md5):
        self.worker.execute(
            "SELECT name FROM image WHERE md5_hash = :hash_val;",
            {"hash_val": md5})
        return self.worker.zip_object(self.worker.get_single_result())

    def find_image_hashes(self, md5):
        self.worker.execute("SELECT a_hash, d_hash, p_hash, reduced_size_factor FROM image_hashes "
                            "WHERE md5_hash = :md5", {"md5": md5})
        return self.worker.zip_objects(self.worker.get_result())

    def find_image_ignore(self, md5, name):
        self.worker.execute("SELECT a.name AS image_1, b.name AS image_2 FROM image_ignore "
                            "JOIN image a ON image_ignore.md5_hash_1 = a.md5_hash "
                            "JOIN image b ON image_ignore.md5_hash_2 = b.md5_hash "
                            "WHERE (md5_hash_1 = :md5 and image_1 = :name) or (md5_hash_2 = :md5 and image_1 = :name)",
                            {"md5": md5, "name": name})
        return self.worker.zip_objects(self.worker.get_result())

    def save_image(self, md5, name, width, height):
        self.worker.execute("INSERT INTO image (md5_hash, name, width, height)"
                            "VALUES (:md5, :name, :width, :height);",
                            {"md5": md5, "name": name, "width": width, "height": height})

    def save_image_hash(self, md5, a_hash, d_hash, p_hash, reduced_size_factor):
        self.worker.execute("SELECT md5_hash WHERE md5_hash = :md5 and reduced_size_factor = :size",
                            {"md5": md5, "size": reduced_size_factor})
        if self.worker.get_result():
            return
        self.worker.execute("INSERT INTO image_hashes (md5_hash, a_hash, d_hash, p_hash, reduced_size_factor) "
                            "VALUES (:md5, :a_hash, :d_hash, :p_hash, :size)",
                            {"md5": md5, "a_hash": a_hash, "d_hash": d_hash,
                             "p_hash": p_hash, "size": reduced_size_factor})

    def save_ignore_similarity(self, md5_1, image_1, md5_2, image_2):
        self.worker.execute("INSERT INTO image_ignore (md5_hash_1, md5_hash_2) VALUES "
                            "(:md5_1, :md5_2)",
                            {"md5_1": md5_1, "md5_2": md5_2})