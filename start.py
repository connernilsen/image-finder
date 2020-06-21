import argparse
import asyncio
from db import image_database_setup as db_setup
from db.database import default_path as default_database_path
from image_load_orchastrator import ImageLoadOrchastrator, default_working_dir

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="An image similarity checker.")
    parser.add_argument("--db-path", metavar="PATH", default=default_database_path,
                        help="The path to the sqlite db file")
    parser.add_argument("--db-timeout", metavar="TIMEOUT", default=5, type=float,
                        help="The db timeout length")
    parser.add_argument("--image-working-dir", metavar="PATH", default=default_working_dir,
                        help="The path to the directory where images are being processed")
    parser.add_argument("--comparison-method", "-m", metavar="METHOD", default="P",
                        choices=["A", "D", "P", "AVERAGE", "DIFFERENCE", "PERCEPTION"],
                        help="The method with which to compare images (see README)")
    parser.add_argument("--precision", "-p", default=2, type=int,
                        help="The amount of characters that can differ in a hash before two images are considered "
                             "different")
    parser.add_argument("--reduced-size-factor", "-s", default=8, type=int,
                        help="How much to reduce the image by when"
                             " creating hash (a higher number will be more precise, but slower)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Display calculated image hashes and diff values")
    args = parser.parse_args()

    db_setup.check_db_version(db_path=args.db_path, db_timeout=args.db_timeout)

    orc = ImageLoadOrchastrator.get_instance(args.image_working_dir, args.db_path, args.db_timeout,
                                             args.verbose)
    asyncio.run(orc.run(args.comparison_method, args.precision, args.reduced_size_factor))

