import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.models import Base

config = context.config


def _apply_runtime_database_url() -> None:
    """Use the active DebateAI database URL for CLI and embedded migrations.

    The INI value is intentionally only a safe, canonical placeholder.  The
    application settings (including .env/DATABASE_URL) are the source of truth,
    so a direct Alembic invocation cannot accidentally target the legacy
    callhelper database or a stale password.
    """
    setter = getattr(config, "set_main_option", None)
    if callable(setter):
        setter("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))


_apply_runtime_database_url()

if (
    config.config_file_name is not None
    and config.attributes.get("configure_logger", True)
):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
