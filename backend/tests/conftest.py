import os
import pytest
from app.core.config import settings

@pytest.fixture(autouse=True)
def setup_test_env():
    # Use SQLite for tests since a real Postgres DB might not be available
    settings.DATABASE_URL = "sqlite:///./test.db"
