import argparse
import asyncio
from db import image_database_setup as db_setup
from db.database import default_path as default_database_path
from image_load_orchastrator import ImageLoadOrchastrator, default_working_dir

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="An image similarity checker.")
    parser.add_argument("--db-path", metavar="PATH", default=default_database_path,
                        help="The path to the sqlite db file")
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
    parser.add_argument("--avoid-db", action="store_true", help="Do not use a db to check if images exist and "
                                                                "don't save images to db")
    parser.add_argument("--drop-db", action="store_true", help="Drop database. Only this command will be run")
    parser.add_argument("--no-migrate", action="store_true",
                        help="Migrations will not be performed if this flag is passed")
    parser.add_argument("--ignore-similarity", "-i", metavar="IMAGE_1_filename IMAGE_2_filename",
                        help="Add the two provided images to a list which considers them different images no matter"
                             "the similarity. Only this command will be run. Files must be in the same working dir",
                        nargs=2)
    parser.add_argument("--verbose", "-v", action="store_true", help="Display calculated image hashes and diff values")
    args = parser.parse_args()

    if args.drop_db or args.rebuild_db:
        db_setup.drop_db(args.db_path, args.verbose)

    if not args.avoid_db and not args.no_migrate:
        db_setup.check_db_version(args.db_path, args.verbose)

    else:
        orc = ImageLoadOrchastrator.get_instance(args.image_working_dir, args.db_path, args.verbose,
                                                 args.precision, args.reduced_size_factor)
        if args.ignore_similarity:
            orc.ignore_similartiy(args.ignore_similarity[0], args.ignore_similarity[1])
        else:
            asyncio.run(orc.run(args.comparison_method, args.avoid_db))

