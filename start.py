import asyncio
from db import image_database_setup as db_setup
from image_orchastrator import ImageOrchastrator

if __name__ == "__main__":
    db_setup.check_db_version()

    orc = ImageOrchastrator.get_instance()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(orc.run())

