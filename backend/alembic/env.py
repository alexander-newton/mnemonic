"""Alembic env for Mnemonic SQLite state DB."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from mnemonic.config import load_config
from mnemonic.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sqlite_url() -> str:
    cfg = load_config()
    db_path = cfg.vault.path / ".mnemonic" / "state.sqlite"
    return f"sqlite:///{db_path}"


def run_migrations_offline() -> None:
    url = _sqlite_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    config_section = config.get_section(config.config_ini_section) or {}
    config_section["sqlalchemy.url"] = _sqlite_url()
    connectable = engine_from_config(config_section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
