import asyncio
from image_worker import ImageWorker
from os import path, listdir
import time


class ImageOrchastrator:
    __instance = None

    @classmethod
    def get_instance(cls, working_dir="./images/", worker_max=9):
        if worker_max % 3 != 0:
            raise RuntimeError("Worker max must be a multiple of 3")
        if cls.__instance is None:
            cls.__instance = cls.__new__(cls)
            cls.__instance.working_dir = working_dir
            cls.sem = asyncio.Semaphore(value=worker_max)
        return cls.__instance

    def __init__(self):
        raise RuntimeError("Call get_instance() instead")

    async def run(self):
        if not path.isdir(self.working_dir):
            raise Exception("Working dir does not exist")

        files = [file for file in listdir(self.working_dir) if path.isfile(
            path.join(self.working_dir, file))]

        workers = []
        start = time.time()
        print(f"Starting... current time is {time.strftime('%H:%M:%S')}")
        for i, file in enumerate(files):
            print(f"Starting file #{i}")
            async with self.sem:
                workers.append(ImageWorker(self.working_dir + str(file)))
            print(f"Done with file #{i}")

        end = time.time()
        diff = end - start
        print(f"Done, finished {len(files)} files. Time is {time.strftime('%H:%M:%S')}, operation took "
              f"{str(diff // 3600).split('.')[0]}:{str(diff // 60).split('.')[0]}:{diff % 60}")

