import asyncio
from image_worker import ImageWorker
from os import path, listdir
import time

default_working_dir = "./images/"
file_types = ["jpeg", "png", "jpg"]


class ImageLoadOrchastrator:
    __instance = None

    @classmethod
    def get_instance(cls, working_dir, db_path, db_timeout, verbose):
        if cls.__instance is None:
            cls.__instance = cls.__new__(cls)
            cls.__instance.working_dir = working_dir
            cls.__instance.db_path = db_path
            cls.__instance.db_timeout = db_timeout
            cls.__instance.verbose = verbose
        return cls.__instance

    def __init__(self):
        raise RuntimeError("Call get_instance() instead")

    async def run(self, comparison_method, precision, reduced_size_factor):
        if not path.isdir(self.working_dir):
            raise Exception("Working dir does not exist")

        files = [file for file in listdir(self.working_dir) if path.isfile(
            path.join(self.working_dir, file))]

        tasks = []
        workers = {}
        start = time.time()
        print(f"Starting... current time is {time.strftime('%H:%M:%S')}")
        for i, file in enumerate(files):
            if file.split(".")[-1] not in file_types:
                continue
            worker = ImageWorker(self.working_dir, str(file), reduced_size_factor)
            tasks.append(asyncio.create_task(worker.construct(comparison_method, self.db_path, self.db_timeout,
                                                              self.verbose)))

        fulfilled_workers = await asyncio.gather(*tasks)

        for i in range(len(fulfilled_workers)):
            worker = fulfilled_workers[i]
            if worker.md5 not in workers:
                workers[worker.md5] = worker
                worker.check_alike(fulfilled_workers[i + 1:], precision)
            else:
                workers[worker.md5].add_exact(worker)

        groups = self.get_groupings(workers)

        end = time.time()
        diff = end - start
        print("Done, finished {file_len} files. Time is {time}, operation took "
              "{hours:.0f}:{minutes:<02.0f}:{seconds:<02.2f}"
              .format(file_len=len(files), time=time.strftime("%H:%M:%S"), hours=diff // 3600,
                      minutes=(diff // 60) % 60, seconds=diff % 60))

    @staticmethod
    def get_groupings(workers):
        found = []
        groups = []

        for md5, worker in workers.items():
            if md5 in found:
                continue

            current = worker.exact.copy()
            current.extend(worker.alike.values())
            found.extend(list(worker.alike.keys()))
            if len(current) > 1:
                groups.append(current)

        return groups
