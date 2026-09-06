from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "name": settings.APP_NAME,
        "message": "CloudGuard backend is running"
    }

def test_health_check():
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.APP_NAME
    assert data["version"] == settings.APP_VERSION
