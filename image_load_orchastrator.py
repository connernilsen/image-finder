import asyncio
from image_worker import ImageWorker
from os import path, listdir
import time

default_working_dir = "./images/"


class ImageLoadOrchastrator:
    __instance = None

    @classmethod
    def get_instance(cls, working_dir, worker_max, db_path, db_timeout):
        if cls.__instance is None:
            cls.__instance = cls.__new__(cls)
            cls.__instance.working_dir = working_dir
            cls.sem = asyncio.Semaphore(value=worker_max)
            cls.db_path = db_path
            cls.db_timeout = db_timeout
        return cls.__instance

    def __init__(self):
        raise RuntimeError("Call get_instance() instead")

    async def run(self, comparison_method, precision):
        if not path.isdir(self.working_dir):
            raise Exception("Working dir does not exist")

        files = [file for file in listdir(self.working_dir) if path.isfile(
            path.join(self.working_dir, file))]

        workers = {}
        exact = {}
        start = time.time()
        print(f"Starting... current time is {time.strftime('%H:%M:%S')}")
        for i, file in enumerate(files):
            async with self.sem:
                worker = ImageWorker(self.working_dir + str(file), comparison_method, self.db_path, self.db_timeout)
                if worker.md5 in workers:
                    if worker.md5 in exact:
                        exact[worker.md5].append(worker)
                    else:
                        exact[worker.md5] = [worker, workers[worker.md5]]
                else:
                    workers[worker.md5] = worker
            print(f"Done with file #{i}")

        alike = await self.compare(workers, comparison_method, precision)

        end = time.time()
        diff = end - start
        print("Done, finished {file_len} files. Time is {time}, operation took "
              "{hours:.0f}:{minutes:<02.0f}:{seconds:<02.2f}"
              .format(file_len=len(files), time=time.strftime("%H:%M:%S"), hours=diff // 3600,
                      minutes=(diff // 60) % 60, seconds=diff % 60))

    async def compare(self, workers, method, precision):
        alike = {}
        for i, image_a in enumerate(workers.values()):
            for image_b in list(workers.values())[i + 1:]:
                async with self.sem:
                    if image_a.compare(image_b, method) <= precision:
                        if image_a.md5 in alike:
                            alike[image_a.md5].append(image_b)
                        else:
                            alike[image_a.md5] = [image_a, image_b]
                        if image_b.md5 in alike:
                            alike[image_b.md5].append(image_a)
                        else:
                            alike[image_b.md5] = [image_b, image_a]
        return alike

