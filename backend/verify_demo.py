import os
from fastapi.testclient import TestClient
from app.main import app

def test_demo_auth():
    client = TestClient(app)
    
    # 1. Invalid credentials rejection
    bad_login = client.post("/api/v1/auth/login", json={
        "email": "demo@cloudguard.io",
        "password": "WrongPassword999!"
    })
    print("[Check 1] Reject invalid credentials status:", bad_login.status_code)
    assert bad_login.status_code == 401

    # 2. Valid Demo login
    demo_password = os.getenv("DEMO_USER_PASSWORD", "DemoPassword123!")
    good_login = client.post("/api/v1/auth/login", json={
        "email": "demo@cloudguard.io",
        "password": demo_password
    })
    print("[Check 2] Demo user login status:", good_login.status_code)
    assert good_login.status_code == 200
    token = good_login.json()["access_token"]
    assert token and len(token) > 20
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Authenticated API request (/auth/me)
    me_res = client.get("/api/v1/auth/me", headers=headers)
    print("[Check 3] /auth/me status:", me_res.status_code, "User:", me_res.json()["email"])
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "demo@cloudguard.io"

    # 4. Workspace listing and authorization
    ws_res = client.get("/api/v1/workspaces", headers=headers)
    print("[Check 4] Workspaces status:", ws_res.status_code)
    assert ws_res.status_code == 200
    workspaces = ws_res.json()
    ws_names = [w["name"] for w in workspaces]
    print("[Check 4] Workspaces found:", ws_names)
    assert "Demonstration Workspace" in ws_names

    demo_ws = next(w for w in workspaces if w["name"] == "Demonstration Workspace")
    demo_ws_id = demo_ws["id"]

    # 5. Dashboard summary for Demonstration Workspace
    dash_res = client.get(f"/api/v1/dashboard/summary?workspace_id={demo_ws_id}", headers=headers)
    print("[Check 5] Dashboard summary status:", dash_res.status_code)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    print("[Check 5] Security score:", dash_data.get("security_score"), "Rating:", dash_data.get("rating"))
    assert dash_data.get("security_score") == 68

    # 6. Findings for Demonstration Workspace
    findings_res = client.get(f"/api/v1/findings?workspace_id={demo_ws_id}", headers=headers)
    print("[Check 6] Findings status:", findings_res.status_code, "Count:", len(findings_res.json()))
    assert findings_res.status_code == 200
    findings = findings_res.json()
    assert len(findings) == 5
    for f in findings:
        print(f"  - [{f['severity']}] {f['title']} (Score: {f.get('risk_score')}, Simulated: {f.get('is_simulated')})")

    # 7. Unauthenticated request rejection to protected endpoint
    unauth_dash = client.get(f"/api/v1/dashboard/summary?workspace_id={demo_ws_id}")
    print("[Check 7] Unauthenticated request rejection status:", unauth_dash.status_code)
    assert unauth_dash.status_code == 401

    # 8. AWS status for Demonstration Workspace
    aws_res = client.get(f"/api/v1/aws/status?workspace_id={demo_ws_id}", headers=headers)
    print("[Check 8] /aws/status status:", aws_res.status_code, "Connected:", aws_res.json().get("connected"))
    assert aws_res.status_code == 200
    assert aws_res.json().get("connected") is True

    # 9. Scans list for Demonstration Workspace
    scans_res = client.get(f"/api/v1/scans?workspace_id={demo_ws_id}", headers=headers)
    print("[Check 9] /scans status:", scans_res.status_code, "Count:", len(scans_res.json()))
    assert scans_res.status_code == 200
    assert len(scans_res.json()) >= 1
    assert scans_res.json()[0].get("is_simulated") is True

    print("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_demo_auth()
