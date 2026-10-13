from logging.config import fileConfig
from sqlalchemy import engine_from_config, create_engine
from sqlalchemy import pool
from alembic import context
from app.models.database import Base
from app.config import settings

config = context.config

try:
    fileConfig(config.config_file)
except (AttributeError, TypeError):
    pass

target_metadata = Base.metadata

def run_migrations_offline():
    url = settings.database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    # Se l'app passa il proprio motore (run_migrations in database.py) si usa quello.
    connectable = config.attributes.get("engine") or create_engine(settings.database_url)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()