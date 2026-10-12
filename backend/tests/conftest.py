import os
import pytest
from app.core.config import settings

@pytest.fixture(autouse=True)
def setup_test_env():
    # Use SQLite for tests since a real Postgres DB might not be available
    settings.DATABASE_URL = "sqlite:///./test.db"
    settings.JWT_SECRET = "test-super-secret-jwt-key-for-testing-only-12345"
    settings.JWT_ALGORITHM = "HS256"
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 60
