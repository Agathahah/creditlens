import os
from dotenv import load_dotenv

load_dotenv()

# Mapping POSTGRES_URL dari .env ke Alembic
config.set_main_option("sqlalchemy.url", os.environ["POSTGRES_URL"])
