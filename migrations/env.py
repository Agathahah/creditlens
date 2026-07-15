"""Alembic environment configuration.

Anchors imports to *this* project's ``src`` package by file location rather
than trusting the ambient ``sys.path`` / ``cwd``. This matters because other
local projects (e.g. a sibling repo also laid out as ``<project>/src/...``)
can leak a same-named top-level ``src`` module into the interpreter via
PYTHONPATH, an editable install, or a stale entry left by a different conda
env — Python then resolves ``import src...`` to whichever one was imported
first, not the one alembic was invoked for.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Evict any "src" (or "src.*") module already cached from a different
# project's directory before importing our own, then make sure this
# project's root is searched first.
for _name in [n for n in sys.modules if n == "src" or n.startswith("src.")]:
    _module_file = getattr(sys.modules[_name], "__file__", None)
    if _module_file is None or PROJECT_ROOT not in Path(_module_file).resolve().parents:
        del sys.modules[_name]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.common.config import get_settings  # noqa: E402
from src.common.database import Base  # noqa: E402

# Import model modules here so their tables register on Base.metadata and
# `alembic revision --autogenerate` can detect them.
# import src.common.models  # noqa: E402,F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().postgres_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emits SQL, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (opens a live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
