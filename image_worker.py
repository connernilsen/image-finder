from db.database_image_handler import DatabaseImageHandler
from hashlib import md5
from math import sqrt, cos, pi
from PIL import Image
from os import mkdir, path, rename
from random import randrange
from typing import List


class ImageWorker:
    def __init__(self, working_dir: str, file: str, reduced_size_factor: int, avoid_db: bool):
        # Set size and calculation values

        # The factor we're reducing the compressed image by
        self.reduced_size_factor = reduced_size_factor
        # The image dimensions we're using for the perception hash
        self.p_hash_resize = reduced_size_factor * 4
        self.p_hash_limit = reduced_size_factor
        # The image dimensions we're using for the difference hash
        self.d_hash_width = self.p_hash_resize + 1
        # Whether or not to avoid db interactions
        self.avoid_db = avoid_db

        # Set values that will be provided or calculated in construct()

        # The name of the file
        self.name = file
        # The working directory
        self.working_dir = working_dir
        # The PIL Image object
        self.image = None
        self.md5 = None
        # Whether or not this should be verbose
        self.verbose = None
        # Whether or not this object is a copy
        self.copy = None
        # Whether or not this image exists in the database
        self.exists = None
        # Whether or not new hashes have been created for this image
        self.new_hashes = True
        # The perception hash value
        self.p_hash = None
        # The average hash value
        self.a_hash = None
        # The difference hash value
        self.d_hash = None
        # The hash algorithm to use in calculations, this is just used for the initial calculation to speed up program
        # run time. If this object ends up getting saved to the database, then the other hash values are calculated too
        self.method = None
        # Whether or not this object has been initialized
        self.initialized = False
        # The path to the database files (SQLite3)
        self.db_path = None
        # Images which this image should be considered not similar to
        self.image_ignore = []
        # A list of hashes for images with different sizes
        self.hashes = []

        # A list of workers with exact matches
        self.exact = []
        # A hash of MD5s to similar image workers
        self.alike = {}

    # Take in specific instance information and update this ImageWorker's information
    async def construct(self, method: str, db_path: str, verbose: bool = False) -> 'ImageWorker':
        self.db_path = db_path
        self.verbose = verbose

        # Mark this object as initialized
        self.initialized = True
        # Determine if the given file exists and is a file
        if not path.exists(self.working_dir + self.name):
            raise Exception(f"Image {self.name} not found")
        if not path.isfile(self.working_dir + self.name):
            raise Exception(f"Image {self.name} is not a file")

        # Open this image and convert to a grayscale image
        self.image = Image.open(self.working_dir + self.name).convert("L")
        # Create an md5 object and calculate the image data hash
        md5_calc = md5()
        md5_calc.update(str(list(self.image.getdata())).encode("utf-8"))
        # Create a hex digest for this image
        self.md5 = md5_calc.hexdigest()
        # Set this image as one of its similar images
        self.alike[self.md5] = self
        self.method = method

        # Initialize the database image value and image handler
        db_img = None
        img_handler = None

        # If we're not avoiding the database, determine if there are any images with this hash already in the db
        if not self.avoid_db:
            img_handler = DatabaseImageHandler(db_path, verbose)
            db_img = img_handler.find_image(self.md5)
            if db_img is not None:
                self.hashes = img_handler.find_image_hashes(self.md5)

        # If no exact image match was found in the db, calculate the hash and set the exists, copy values to false
        if db_img is None or self.reduced_size_factor not in self.hashes:
            self.calculate_single_hash(self.method)

            self.exists = False
            self.copy = False
        else:
            # Get a list of the other hashes saved for this image
            # If there already exists a value for this object's hashes, get them all
            if self.hashes[self.reduced_size_factor]:
                self.a_hash = self.hashes[self.reduced_size_factor]['a_hash']
                self.p_hash = self.hashes[self.reduced_size_factor]['p_hash']
                self.d_hash = self.hashes[self.reduced_size_factor]['d_hash']
                self.new_hashes = False
            # Otherwise calculate a new hash
            else:
                self.calculate_single_hash(method)
                self.new_hashes = True
            # Determine if this image is only a copy (by the name of the file)
            self.exists = True
            self.copy = db_img['name'] != self.name

            # Get all ignored images
            self.image_ignore = img_handler.find_image_ignore(self.md5, self.name)
            if self.image_ignore is None:
                self.image_ignore = []

        return self

    # Calculate only the given hash
    def calculate_single_hash(self, method: str) -> None:
        if method == "P" or method == "PERCEPTION":
            self.p_hash = self.perception_hash()
        else:
            self.p_hash = None
        if method == "A" or method == "AVERAGE":
            self.a_hash = self.average_hash()
        else:
            self.a_hash = None
        if method == "D" or method == "DIFFERENCE":
            self.d_hash = self.difference_hash()
        else:
            self.d_hash = None

    # Check if this object has been initialized and throw an exception otherwise
    def check_init(self) -> None:
        if self.initialized is False:
            raise Exception("Worker was not initialized")

    def add_exact(self, dup: 'ImageWorker') -> None:
        self.check_init()
        # If this image has already been added
        if dup.name in self.image_ignore:
            pass
        self.exact.append(dup)

    def check_alike(self, images: List['ImageWorker'], precision: int) -> None:
        self.check_init()
        for worker in images:
            # If worker is in this worker's list of exact or alike matches, skip
            if worker.md5 == self.md5 or worker.md5 in self.alike:
                continue
            # If worker is in this worker's list of images to ignore, skip
            if worker.name in self.image_ignore:
                continue
            # Otherwise, compare both workers
            similarity = self.compare(worker, self.method)
            # Determine if they're enough alike
            if similarity <= precision:
                # If so, combine the workers lists of alike and set each both lists to be the same
                self.alike.update(worker.alike)
                worker.alike = self.alike

    # The average hash algorithm
    # Finds the average value of all pixels and determines if each individual is higher or lower
    def average_hash(self) -> str:
        self.check_init()
        # Resize the image
        new_image = self.image.resize((self.reduced_size_factor, self.reduced_size_factor))
        # Get a list of the pixels
        image_data = list(new_image.getdata())

        # Find the average value of the pixels
        avg = sum(image_data) / self.reduced_size_factor ** 2

        # Get a list of the individual bits (1 if the bit >= average, 0 if <)
        bits = [int(bit >= avg) for bit in image_data]

        # Return the hex'd hash
        return self.create_hash(bits)

    # The perception hash algorithm
    # Runs a DCT on the pixel data and gets the average value of the returned values, then performs an average hash
    def perception_hash(self) -> str:
        self.check_init()
        # Resize image
        new_image = self.image.resize((self.p_hash_resize, self.p_hash_resize))
        # Perform DCT
        dct = self.discrete_cosine_transform(list(new_image.getdata()))

        # Get the average value of the returned DCT data
        avg_dct = 0
        for i, row in enumerate(dct):
            for j, item in enumerate(row):
                if i == j == 0:
                    continue
                avg_dct += item
        avg_dct /= (len(dct) ** 2 - 1)

        # Runs average hash
        bits = [int(bit >= avg_dct) for row in dct for bit in row]

        # Return the hex'd hash
        return self.create_hash(bits)

    # Algorithm idea from
    # https://www.geeksforgeeks.org/discrete-cosine-transform-algorithm-program/
    # The discrete cosine transform algorithm (DCT)
    # Transforms a list of color values into a list of color value frequencies
    # Slowest but most accurate algorithm
    def discrete_cosine_transform(self, decomposed_matrix: List) -> List[List[int]]:
        self.check_init()
        # Create a 2D matrix of the provided list, cutting off each row after p_hash_resize length
        matrix = []
        for i in range(self.p_hash_resize):
            matrix.append(decomposed_matrix[self.p_hash_resize * i:self.p_hash_resize * (i + 1)])

        # Get commonly used values and set up output matrix
        output = []
        m_len = len(matrix)
        sqrt2 = sqrt(2)

        # Loop through matrix rows and calculate dct sum
        for i in range(self.p_hash_limit):
            # Get the row and row length, and append and empty list to the output list
            row = matrix[i]
            r_len = len(row)
            output.append([])

            # Loop through matrix columns
            for j in range(self.p_hash_limit):
                # Calculate ci and cj values, which are (1 or sqrt2) / (sqrt(m_len and r_len), depending on whether or
                # not this is the first row/column or not
                ci = (1 if i == 0 else sqrt2) / sqrt(m_len)
                cj = (1 if j == 0 else sqrt2) / sqrt(r_len)

                # Calculate the DCT for each given subrow/item combination
                current_sum = 0
                for k, sub_row in enumerate(matrix):
                    for l, sub_item in enumerate(sub_row):
                        dct = sub_item * cos((2 * k + 1) * i * pi / (2 * m_len)) \
                              * cos((2 * l + 1) * j * pi / (2 * r_len))

                        # Append the calculated item DCT to the current sum
                        current_sum += dct

                # Append the DCT sum for the current row to the output matrix
                output[i].append(ci * cj * current_sum)

        return output

    # Calculate gradient difference
    def difference_hash(self) -> str:
        self.check_init()
        # Resize the image
        new_image = self.image.resize((self.d_hash_width, self.p_hash_resize))
        decomposed_matrix = list(new_image.getdata())

        # Get a matrix of the pixel values
        matrix = []
        for i in range(self.p_hash_resize):
            matrix.append(decomposed_matrix[self.d_hash_width * i:self.d_hash_width * (i + 1)])

        # Calculate the difference between this pixel and the previous pixel (not counting the first row)
        bits = []
        for i in range(len(matrix)):
            for j in range(1, len(matrix[i])):
                bits.append(int(matrix[i][j] > matrix[i][j - 1]))

        return self.create_hash(bits)

    # Compare two different hashes and return the Hamming distance
    def compare(self, other_image: 'ImageWorker', method: str = "P") -> int:
        self.check_init()
        if method == "P" or "PERCEPTION":
            value = self._compare_p_hash(other_image)
        elif method == "A" or "AVERAGE":
            value = self._compare_a_hash(other_image)
        else:
            value = self._compare_d_hash(other_image)

        if self.verbose:
            print(f"Hash comparison \n  [{self.working_dir}{self.name}]\n  "
                  f"[{other_image.working_dir}{other_image.name}]\n\n result: {value}")

        return value

    def _compare_a_hash(self, other_image: 'ImageWorker') -> int:
        return self.hamming_distance(self.a_hash, other_image.a_hash)

    def _compare_p_hash(self, other_image: 'ImageWorker') -> int:
        return self.hamming_distance(self.p_hash, other_image.p_hash)

    def _compare_d_hash(self, other_image: 'ImageWorker') -> int:
        return self.hamming_distance(self.d_hash, other_image.d_hash)

    # Uses Hamming distance algorithm
    @staticmethod
    def hamming_distance(hash_a: str, hash_b: str) -> int:
        # Just return really high value if one image doesn't have a hash
        if hash_a is None:
            print("This image has no hash")
            return 256
        if hash_b is None:
            print("Other image has no hash")
            return 256
        # Make sure the hash lengths are the same
        if len(hash_a) != len(hash_b):
            raise Exception(f"Hash lengths were not the same, a: {len(hash_a)} b: {len(hash_b)}")
        distance = 0
        # Loop through each value and increment the distance by 1 if the characters don't match
        for i in range(len(hash_a)):
            if hash_a[i] != hash_b[i]:
                distance += 1

        return distance

    # Create a hexadecimal hash from the given binary integer array
    def create_hash(self, arr: List[int]) -> str:
        self.check_init()
        # Convert from binary array to integer
        res = 0
        for i, num in enumerate(arr):
            res += 2 ** i * num

        # Convert from integer to hexadecimal
        hex_val = hex(res)
        if self.verbose:
            print(f"Hash value [{self.working_dir}{self.name}]: {hex_val}")
        return hex_val

    # Move this image into the provided directory (the directory should not exist)
    def move(self, new_path: str) -> None:
        self.check_init()
        curr_path = path.join(self.working_dir, self.name)
        if not path.exists(curr_path):
            raise Exception(f"Image {self.name} not found before move")
        if not path.isfile(curr_path):
            raise Exception(f"Image {self.name} is not a file")
        if not path.exists(new_path):
            raise Exception(f"new_path variable {new_path} does not exist")

        # Move all exact images into a subdirectory first and then move this image into the same
        if len(self.exact) != 0:
            suffix = hex(randrange(0, 2 ** 10))
            updated_path = path.join(new_path, suffix)
            mkdir(updated_path)

            # Move exact images
            for exact_image in self.exact:
                rename(path.join(exact_image.working_dir, exact_image.name),
                       path.join(updated_path, exact_image.name))

            # Move this image
            rename(path.join(self.working_dir, self.name),
                   path.join(updated_path, self.name))
        # If there are no exact matches, then just move this image into the new_path
        else:
            rename(path.join(self.working_dir, self.name),
                   path.join(new_path, self.name))

    # Finish creating all other hashes before save
    def complete(self) -> None:
        if self.a_hash is None:
            self.a_hash = self.average_hash()
        if self.d_hash is None:
            self.d_hash = self.difference_hash()
        if self.p_hash is None:
            self.p_hash = self.perception_hash()

    # Save the image's data to the database if not avoiding database
    async def save_image_data(self) -> None:
        self.check_init()
        if self.avoid_db:
            print("Avoid_db set, skipping insertion...")
            return
        if self.exists and not self.new_hashes:
            return

        # Finish creating all other hashes
        self.complete()

        # Save the new item or the new hashes depending on whether or not the image exists in the database
        image_handler = DatabaseImageHandler(self.db_path, self.verbose)
        if not self.exists:
            image_handler.save_image(self.md5, self.name, self.image.width, self.image.height)
        if self.new_hashes:
            image_handler.save_image_hash(self.md5, self.a_hash, self.d_hash, self.p_hash, self.reduced_size_factor)

    # Save an ignore_similarity request to the database
    def save_ignore_similarity(self, other):
        self.check_init()
        other.check_init()
        if self.name <= other.name:
            first = self
            second = other
        else:
            first = other
            second = self

        image_handler = DatabaseImageHandler(self.db_path, self.verbose)
        image_handler.save_ignore_similarity(first.md5, first.name, second.md5, second.name)
