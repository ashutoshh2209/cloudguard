import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import Base
from app.core.database import get_db
from app.models.aws_connection import AWSConnection
from app.models.scan import Scan
from app.models.finding import Finding
from app.models.resource import CloudResource
from app.models.category_score import CategoryScore

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    conn = AWSConnection(
        id="conn-1",
        account_id="123456789012",
        role_arn="arn:aws:iam::123456789012:role/CloudGuard",
        region="us-east-1"
    )
    db.add(conn)
    db.commit()

    scan = Scan(
        id="scan-1",
        aws_connection_id="conn-1",
        status="COMPLETED",
        resources_scanned=2,
        checks_attempted=5,
        checks_completed=5,
        checks_failed=1,
        coverage_percentage=100,
        security_score=85,
        security_rating="B"
    )
    db.add(scan)
    db.commit()

    resource = CloudResource(
        id="res-1",
        scan_id="scan-1",
        aws_connection_id="conn-1",
        resource_id="bucket-1",
        resource_type="AWS::S3::Bucket",
        service="s3",
        name="my-bucket",
        region="us-east-1",
        status="active",
        metadata_json={"public": True}
    )
    db.add(resource)

    finding = Finding(
        id="finding-1",
        scan_id="scan-1",
        resource_id="bucket-1",
        rule_id="s3-public-access",
        title="S3 Bucket Publicly Accessible",
        description="Bucket allows public read.",
        severity="HIGH",
        category="Storage",
        risk_score=75,
        priority="P2",
        status="OPEN",
        recommendation="Enable block public access.",
        evidence={"acl": "public-read"}
    )
    db.add(finding)

    cat_score = CategoryScore(
        id="cs-1",
        scan_id="scan-1",
        category="Storage",
        score=75,
        status="warning",
        finding_count=1,
        critical_count=0,
        high_count=1
    )
    db.add(cat_score)

    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)

def test_list_scans_and_get_scan():
    response = client.get("/api/v1/scans/")
    assert response.status_code == 200
    scans = response.json()
    assert len(scans) >= 1
    assert scans[0]["id"] == "scan-1"
    assert scans[0]["summary"]["resources_scanned"] == 2

    single_response = client.get("/api/v1/scans/scan-1")
    assert single_response.status_code == 200
    scan_data = single_response.json()
    assert scan_data["id"] == "scan-1"
    assert scan_data["security_score"] == 85

def test_list_resources():
    response = client.get("/api/v1/resources/?scan_id=scan-1")
    assert response.status_code == 200
    resources = response.json()
    assert len(resources) == 1
    assert resources[0]["resource_id"] == "bucket-1"
    assert resources[0]["resource_name"] == "my-bucket"
    assert resources[0]["details"] == {"public": True}

def test_reports_lifecycle():
    # 1. Create Report
    post_res = client.post("/api/v1/reports/?scan_id=scan-1")
    assert post_res.status_code == 200
    report = post_res.json()
    assert report["scan_id"] == "scan-1"
    report_id = report["id"]

    # 2. List Reports
    list_res = client.get("/api/v1/reports/")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1

    # 3. Get Report Detail
    detail_res = client.get(f"/api/v1/reports/{report_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["report"]["id"] == report_id
    assert detail["security_posture"]["score"] == 85
    assert len(detail["top_findings"]) == 1
    assert detail["top_findings"][0]["finding_id"] == "finding-1"

    # 4. Download Report PDF
    pdf_res = client.get(f"/api/v1/reports/{report_id}/download")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 0
