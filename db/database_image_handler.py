from db.database_worker import DatabaseWorker, default_path
from typing import Dict, List


class DatabaseImageHandler:
    def __init__(self, db_path: str, verbose: bool):
        # Create a database worker for this image handler
        self.worker = DatabaseWorker(db_path, verbose)

    # Find an image by a given MD5
    def find_image(self, md5: str) -> Dict[str, any]:
        self.worker.execute(
            "SELECT name FROM image WHERE md5_hash = :hash_val;",
            {"hash_val": md5})
        return self.worker.zip_object(self.worker.get_single_result())

    # Find existing hashes by a given MD5
    def find_image_hashes(self, md5: str) -> List[Dict[str, any]]:
        self.worker.execute("SELECT a_hash, d_hash, p_hash, reduced_size_factor FROM image_hashes "
                            "WHERE md5_hash = :md5", {"md5": md5})
        # Get a list of hashes of different size factors from a given MD5
        hash_ls = self.worker.zip_objects(self.worker.get_result())
        # Create a dictionary with size factor to item
        return {item["reduced_size_factor"]: item for item in hash_ls}

    # Find a possibly existing image ignore request
    def find_image_ignore(self, md5: str, name: str) -> List[Dict[str, any]]:
        self.worker.execute("SELECT a.name AS image_1, b.name AS image_2 FROM image_ignore "
                            "JOIN image a ON image_ignore.md5_hash_1 = a.md5_hash "
                            "JOIN image b ON image_ignore.md5_hash_2 = b.md5_hash "
                            "WHERE (md5_hash_1 = :md5 and image_1 = :name) or (md5_hash_2 = :md5 and image_1 = :name)",
                            {"md5": md5, "name": name})
        return self.worker.zip_objects(self.worker.get_result())

    # Save an image's information
    def save_image(self, md5: str, name: str, width: int, height: int) -> None:
        self.worker.execute("INSERT INTO image (md5_hash, name, width, height)"
                            "VALUES (:md5, :name, :width, :height);",
                            {"md5": md5, "name": name, "width": width, "height": height})
        self.worker.commit_changes()

    # Save an image's hash information
    def save_image_hash(self, md5: str, a_hash: str, d_hash: str, p_hash: str, reduced_size_factor: int) -> None:
        self.worker.execute("SELECT md5_hash FROM image_hashes WHERE md5_hash = :md5 and reduced_size_factor = :size",
                            {"md5": md5, "size": reduced_size_factor})
        if self.worker.get_result():
            return
        self.worker.execute("INSERT INTO image_hashes (md5_hash, a_hash, d_hash, p_hash, reduced_size_factor) "
                            "VALUES (:md5, :a_hash, :d_hash, :p_hash, :size)",
                            {"md5": md5, "a_hash": a_hash, "d_hash": d_hash,
                             "p_hash": p_hash, "size": reduced_size_factor})
        self.worker.commit_changes()

    # Save an image ignore request
    def save_ignore_similarity(self, md5_1: str, md5_2: str):
        self.worker.execute("INSERT INTO image_ignore (md5_hash_1, md5_hash_2) VALUES "
                            "(:md5_1, :md5_2)",
                            {"md5_1": md5_1, "md5_2": md5_2})
