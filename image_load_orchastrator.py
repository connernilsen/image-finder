import asyncio
from image_worker import ImageWorker
from os import path, listdir, mkdir
import time
from random import randrange
from typing import Dict, List

default_working_dir = "./images/"
file_types = ["jpeg", "png", "jpg"]


class ImageLoadOrchastrator:
    __instance = None

    @classmethod
    def get_instance(cls, working_dir, db_path, verbose, precision, reduced_size_factor) -> 'ImageLoadOrchastrator':
        # Create singleton of this class, and return the existing instance if it exists
        if cls.__instance is None:
            cls.__instance = cls.__new__(cls)
            # The working directory of the image
            cls.__instance.working_dir = working_dir
            # The path to the database files (SQLite3)
            cls.__instance.db_path = db_path
            # Whether or not to be verbose
            cls.__instance.verbose = verbose
            # The precision (how many different characters allowed in the hash) for determining likeness
            cls.__instance.precision = precision
            # The factor to reduce the image size by
            cls.__instance.reduced_size_factor = reduced_size_factor
        return cls.__instance

    # Only allow creation through get_instance method
    def __init__(self):
        raise RuntimeError("Call get_instance() instead")

    # Run the comparison routine
    async def run(self, comparison_method: str, avoid_db: bool) -> None:
        # Make sure the provided path to images exists
        if not path.isdir(self.working_dir):
            raise Exception("Working dir does not exist")

        # Get all images from the working dir provided
        files = [file for file in listdir(self.working_dir) if path.isfile(
            path.join(self.working_dir, file))]

        # Initialize the start time (for stats purposes) and list of tasks
        tasks = []
        start = time.time()
        print(f"Starting... current time is {time.strftime('%H:%M:%S')}")

        # Create an async worker for each file (to get a hash of the file) and run
        for i, file in enumerate(files):
            # Make sure the filetype is one of the allowed types
            if file.split(".")[-1] not in file_types:
                continue
            # Create the ImageWorker for the image, start it, and append the task to our list of tasks
            worker = ImageWorker(self.working_dir, str(file), self.reduced_size_factor, avoid_db)
            tasks.append(asyncio.create_task(worker.construct(comparison_method, self.db_path,
                                                              self.verbose)))

        # Wait until all workers are done and gather into a list of completed workers
        fulfilled_workers = await asyncio.gather(*tasks)

        # Get workers (trim out all exact matches) and find similar images
        workers = await self.get_workers(fulfilled_workers)

        # Get groupings of alike and exact matches
        groups = self.get_groupings(workers)

        # Move each image into its new folder for comparison
        self.move_groups(groups)

        # Finish by saving all images to the database if we're not avoiding it
        if not avoid_db:
            await self.save_image_data(workers)

        end = time.time()
        diff = end - start
        print("Done, finished {file_len} files. Time is {time}, operation took "
              "{hours:.0f}:{minutes:<02.0f}:{seconds:<02.2f}"
              .format(file_len=len(files), time=time.strftime("%H:%M:%S"), hours=diff // 3600,
                      minutes=(diff // 60) % 60, seconds=diff % 60))

    # Group all alike and exact images together
    @staticmethod
    def get_groupings(workers: Dict[str, ImageWorker]) -> List[List[ImageWorker]]:
        found = []
        groups = []

        # Loop through all workers (excluding those trimmed)
        for md5, worker in workers.items():
            # Skip if the MD5 was already found
            if md5 in found:
                continue

            # Copy the alike workers
            current = worker.alike.values()
            # Add all found MD5s to the found list so that files aren't moved multiple times
            found.extend(list(worker.alike.keys()))
            # Only append to the return list of groups if there are results
            if len(current) > 1:
                groups.append(current)

        return groups

    # Trim down workers with the exact same MD5
    async def get_workers(self, fulfilled_workers) -> Dict[str, ImageWorker]:
        workers = {}
        # Search through all workers
        for i in range(len(fulfilled_workers)):
            worker = fulfilled_workers[i]

            # If no other worker with the given MD5 exists, add this and find all similar workers throughout the rest of
            # the list
            if worker.md5 not in workers:
                workers[worker.md5] = worker
                worker.check_alike(fulfilled_workers[i + 1:], self.precision)
            # Otherwise, add this worker to the already existing workers list of exact matches
            else:
                workers[worker.md5].add_exact(worker)
        return workers

    # Loop through and move groups of images into new folders
    def move_groups(self, groups: List[List[ImageWorker]]) -> None:
        # Loop through and move each group
        for group in groups:
            # Create some random numerical suffix from 0 to 2^50
            random_suffix = hex(randrange(0, 2**50))
            # get the new path
            new_path = path.join(self.working_dir, random_suffix)
            # Create the new directory
            mkdir(new_path)
            # Asynchronously move all images into the new directory
            for image in group:
                image.move(new_path)

    # Save all images to the database
    @staticmethod
    async def save_image_data(workers: List[ImageWorker]) -> None:
        tasks = []
        for worker in workers.values():
            tasks.append(asyncio.create_task(worker.save_image_data()))

        await asyncio.gather(*tasks)

    # Add an ignore similarity request
    def ignore_similarity(self, image_1_name: str, image_2_name: str) -> None:
        if not path.isdir(self.working_dir):
            raise Exception("Working dir does not exist")
        image_1 = ImageWorker(self.working_dir, image_1_name, self.reduced_size_factor, False)
        image_2 = ImageWorker(self.working_dir, image_2_name, self.reduced_size_factor, False)

        image_1.construct(None, self.db_path, self.verbose)
        image_2.construct(None, self.db_path, self.verbose)

        image_1.save_image_data()
        image_2.save_image_data()

        image_1.save_ignore_similarity(image_2)


