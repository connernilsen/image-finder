import base64
from db.database_image_handler import DatabaseImageHandler
from hashlib import md5
from math import sqrt, cos, pi
from PIL import Image


class ImageWorker:
    avg_hash_resize = 8
    p_hash_resize = 32
    p_hash_limit = 8
    d_hash_width = avg_hash_resize + 1

    def __init__(self, file, calculate_p_hash=True):
        self.file = file
        self.image = Image.open(file).convert("L")
        md5_calc = md5()
        md5_calc.update(str(list(self.image.getdata())).encode("utf-8"))
        self.md5 = md5_calc.hexdigest()

        img_handler = DatabaseImageHandler()
        db_img = img_handler.find_image(self.md5)

        if db_img is None:
            self.a_hash = self.average_hash()
            if calculate_p_hash:
                self.p_hash = self.perception_hash()
            else:
                self.p_hash = None
            self.d_hash = self.difference_hash()
        else:
            self.a_hash = db_img["a_hash"]
            self.p_hash = db_img["p_hash"]
            self.d_hash = db_img["d_hash"]

    # Algorithm overview from
    # https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    def average_hash(self):
        new_image = self.image.resize((self.avg_hash_resize, self.avg_hash_resize))
        image_data = list(new_image.getdata())

        avg = sum(image_data) / self.avg_hash_resize ** 2

        bits = [int(bit >= avg) for bit in image_data]

        return self.create_hash(bits)

    def perception_hash(self):
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
        new_image = self.image.resize((self.d_hash_width, self.avg_hash_resize))
        decomposed_matrix = list(new_image.getdata())
        matrix = []
        for i in range(self.avg_hash_resize):
            matrix.append(decomposed_matrix[self.d_hash_width * i:self.d_hash_width * (i + 1)])

        bits = []
        for i in range(len(matrix)):
            for j in range(1, len(matrix[i])):
                bits.append(int(matrix[i][j] > matrix[i][j - 1]))

        return self.create_hash(bits)

    def compare_a_hash(self, other_image):
        return self.hamming_distance(self.a_hash, other_image.a_hash)

    def compare_p_hash(self, other_image):
        if self.p_hash is None:
            print("This image has no hash")
            return 256
        if other_image.p_hash is None:
            print ("Other image has no hash")
            return 256
        return self.hamming_distance(self.p_hash, other_image.p_hash)

    def compare_d_hash(self, other_image):
        return self.hamming_distance(self.d_hash, other_image.d_hash)

    # Uses Hamming distance algorithm
    @staticmethod
    def hamming_distance(hash_a, hash_b):
        if len(hash_a) != len(hash_b):
            raise Exception(f"Hash lengths were not the same, a: {len(hash_a)} b: {len(hash_b)}")
        distance = 0
        for i in range(len(hash_a)):
            if hash_a[i] != hash_b[i]:
                distance += 1

        return distance

    @staticmethod
    def create_hash(arr):
        res = 0
        for i, num in enumerate(arr):
            res += 2**i * num

        return hex(res)
