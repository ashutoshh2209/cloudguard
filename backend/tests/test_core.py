from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_database_config():
    # Database config is correctly loaded
    assert "sqlite" in settings.DATABASE_URL or "postgresql" in settings.DATABASE_URL
    assert settings.DATABASE_URL is not None

def test_error_handling():
    # Test global exception handler (could be triggered by a missing route returning 404, or throwing an internal error)
    response = client.get("/nonexistent-route")
    assert response.status_code == 404

    # The exception handler tests would ideally trigger a 500, but without a dedicated endpoint 
    # to throw an error, we just verify the route works. 
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
