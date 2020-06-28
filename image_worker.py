from db.database_image_handler import DatabaseImageHandler
from hashlib import md5
from math import sqrt, cos, pi
from PIL import Image
from os import mkdir, path
from random import randrange


class ImageWorker:
    def __init__(self, working_dir, file, reduced_size_factor, avoid_db):
        # Set size and calculation values
        self.avg_hash_resize = reduced_size_factor
        self.p_hash_resize = reduced_size_factor * 4
        self.p_hash_limit = reduced_size_factor
        self.d_hash_width = self.p_hash_resize + 1
        self.avoid_db = avoid_db

        # Set values that will be provided or calculated in construct()
        self.name = file
        self.working_dir = working_dir
        self.image = None
        self.md5 = None
        self.verbose = None
        self.copy = None
        self.exists = None
        self.p_hash = None
        self.a_hash = None
        self.d_hash = None
        self.method = None
        self.initialized = False
        self.db_path = None
        self.db_timeout = None

        # Set values that will be updated later on
        self.exact = []
        self.alike = {}

    async def construct(self, method, db_path, db_timeout, verbose=False):
        self.db_path = db_path
        self.db_timeout = db_timeout
        self.initialized = True
        self.verbose = verbose
        if not path.exists(self.working_dir + self.name):
            raise Exception(f"Image {self.name} not found")
        if not path.isfile(self.working_dir + self.name):
            raise Exception(f"Image {self.name} is not a file")
        self.image = Image.open(self.working_dir + self.name).convert("L")
        md5_calc = md5()
        md5_calc.update(str(list(self.image.getdata())).encode("utf-8"))
        self.md5 = md5_calc.hexdigest()
        self.alike[self.md5] = self
        self.method = method

        db_img = None
        if not self.avoid_db:
            img_handler = DatabaseImageHandler(db_path, db_timeout)
            db_img = img_handler.find_image(self.md5)

        if db_img is None or db_img[4] != self.avg_hash_resize:
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

            self.exists = False
            self.copy = False
        else:
            self.a_hash = db_img[1]
            self.p_hash = db_img[2]
            self.d_hash = db_img[3]
            self.exists = True
            if db_img[0] == self.name:
                self.copy = False
            else:
                self.exists = True

        return self

    def check_init(self):
        if self.initialized is False:
            raise Exception("Worker was not initialized")

    def add_exact(self, dup):
        self.check_init()
        self.exact.append(dup)

    def check_alike(self, images, precision):
        self.check_init()
        for worker in images:
            if worker.md5 == self.md5:
                continue
            if worker.md5 in self.alike:
                continue
            similarity = self.compare(worker, self.method)
            if similarity <= precision:
                self.alike.update(worker.alike)
                worker.alike = self.alike

    # Algorithm overview from
    # https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    def average_hash(self):
        self.check_init()
        new_image = self.image.resize((self.avg_hash_resize, self.avg_hash_resize))
        image_data = list(new_image.getdata())

        avg = sum(image_data) / self.avg_hash_resize ** 2

        bits = [int(bit >= avg) for bit in image_data]

        return self.create_hash(bits)

    def perception_hash(self):
        self.check_init()
        new_image = self.image.resize((self.p_hash_resize, self.p_hash_resize))
        dct = self.discrete_cosine_transform(list(new_image.getdata()))

        avg_dct = 0
        for i, row in enumerate(dct):
            for j, item in enumerate(row):
                if i == j == 0:
                    continue
                avg_dct += item
        avg_dct /= (len(dct) ** 2 - 1)

        bits = [int(bit >= avg_dct) for row in dct for bit in row]

        return self.create_hash(bits)

    # Algorithm from
    # https://www.geeksforgeeks.org/discrete-cosine-transform-algorithm-program/
    def discrete_cosine_transform(self, decomposed_matrix):
        self.check_init()
        matrix = []
        for i in range(self.p_hash_resize):
            matrix.append(decomposed_matrix[self.p_hash_resize * i:self.p_hash_resize * (i + 1)])

        output = []
        m_len = len(matrix)
        sqrt2 = sqrt(2)

        for i in range(self.p_hash_limit):
            row = matrix[i]
            r_len = len(row)
            output.append([])
            for j in range(self.p_hash_limit):
                ci = (1 if i == 0 else sqrt2) / sqrt(m_len)
                cj = (1 if j == 0 else sqrt2) / sqrt(r_len)

                current_sum = 0
                for k, sub_row in enumerate(matrix):
                    for l, sub_item in enumerate(sub_row):
                        dct = sub_item * cos((2 * k + 1) * i * pi / (2 * m_len)) \
                              * cos((2 * l + 1) * j * pi / (2 * r_len))

                        current_sum += dct

                output[i].append(ci * cj * current_sum)

        return output

    # Calculate gradient difference
    def difference_hash(self):
        self.check_init()
        new_image = self.image.resize((self.d_hash_width, self.p_hash_resize))
        decomposed_matrix = list(new_image.getdata())
        matrix = []
        for i in range(self.p_hash_resize):
            matrix.append(decomposed_matrix[self.d_hash_width * i:self.d_hash_width * (i + 1)])

        bits = []
        for i in range(len(matrix)):
            for j in range(1, len(matrix[i])):
                bits.append(int(matrix[i][j] > matrix[i][j - 1]))

        return self.create_hash(bits)

    def compare(self, other_image, method="P"):
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

    def _compare_a_hash(self, other_image):
        return self.hamming_distance(self.a_hash, other_image.a_hash)

    def _compare_p_hash(self, other_image):
        return self.hamming_distance(self.p_hash, other_image.p_hash)

    def _compare_d_hash(self, other_image):
        return self.hamming_distance(self.d_hash, other_image.d_hash)

    # Uses Hamming distance algorithm
    @staticmethod
    def hamming_distance(hash_a, hash_b):
        if hash_a is None:
            print("This image has no hash")
            return 256
        if hash_b is None:
            print ("Other image has no hash")
            return 256
        if len(hash_a) != len(hash_b):
            raise Exception(f"Hash lengths were not the same, a: {len(hash_a)} b: {len(hash_b)}")
        distance = 0
        for i in range(len(hash_a)):
            if hash_a[i] != hash_b[i]:
                distance += 1

        return distance

    def create_hash(self, arr):
        self.check_init()
        res = 0
        for i, num in enumerate(arr):
            res += 2**i * num

        hex_val = hex(res)
        if self.verbose:
            print(f"Hash value [{self.working_dir}{self.name}]: {hex_val}")
        return hex_val

    def move(self, new_path):
        self.check_init()
        curr_path = self.working_dir + self.name
        if not path.exists(curr_path):
            raise Exception(f"Image {self.name} not found before move")
        if not path.isfile(curr_path):
            raise Exception(f"Image {self.name} is not a file")
        if len(self.exact) != 0:
            suffix = hex(randrange(0, 2**50))
            new_path = path.join(new_path, suffix)
            # TODO is this filemode right?
            mkdir(updated_path, 0)
        # TODO figure out how to move image
        # TODO move exact images into the same dir

    def save_image_data(self):
        self.check_init()
        if self.avoid_db:
            raise Exception("avoid_db set but attempting to insert into db")
        if self.exists:
            return

        if self.a_hash is None:
            self.a_hash = self.average_hash()
        if self.d_hash is None:
            self.d_hash = self.difference_hash()
        if self.p_hash is None:
            self.p_hash = self.perception_hash()

        self.__save()

    def __save(self):
        image_handler = DatabaseImageHandler(self.db_path, self.db_timeout)
        image_handler.save_image(self.md5, self.a_hash, self.d_hash, self.p_hash, self.name,
                                 self.avg_hash_resize, self.image.width, self.image.height)
