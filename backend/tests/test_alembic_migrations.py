import os
import tempfile
import pytest
from alembic.config import Config
from alembic import command


def test_alembic_migrations_upgrade_and_downgrade():
    """
    Verifies that all Alembic migrations execute cleanly from base to head
    and can be downgraded back to base without schema or dialect errors.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ini_path = os.path.join(backend_dir, "alembic.ini")

        alembic_cfg = Config(ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", sqlite_url)
        alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))

        # Upgrade all migrations to head
        command.upgrade(alembic_cfg, "head")

        # Downgrade all migrations to base
        command.downgrade(alembic_cfg, "base")

        # Upgrade again to ensure idempotent re-application
        command.upgrade(alembic_cfg, "head")

    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass
