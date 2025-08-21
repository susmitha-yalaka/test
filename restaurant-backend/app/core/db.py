from databases import Database
from . import config


database = Database(config.DATABASE_URL)
