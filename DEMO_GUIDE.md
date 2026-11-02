# CloudGuard - Local Professor Demonstration Guide

This guide describes how to run and demonstrate the CloudGuard security posture assessment platform locally for evaluation, without deploying public infrastructure.

---

## 1. Architecture & Security Highlights

- **Standard Authentication**: Uses standard bcrypt password hashing (with byte slicing to safely conform to bcrypt's 72-byte max specification) and signed JWT tokens with HS256.
- **Strict Authorization**: Zero authentication bypasses or backdoors. Every protected endpoint strictly requires valid JWT bearer tokens and validates workspace membership (anti-IDOR).
- **Hybrid Demonstration Architecture**:
  - **Demonstration Workspace**: Contains deterministic, clearly labeled simulated cloud resources and findings (`[SIMULATED]`) for offline grading and demonstration.
  - **Personal Workspace**: Fully isolated clean-slate workspace for connecting live AWS accounts via AWS STS `AssumeRole`. Simulated findings never mix into live scans or live security scores.
- **Zero Secrets Logging**: Credentials, tokens, and IAM secrets are never logged or exposed to the client.

---

## 2. Environment Variables

Local demo credentials can be customized in `backend/.env`:

```env
# Database (SQLite by default for local development, or PostgreSQL)
DATABASE_URL=sqlite:///./cloudguard.db

# JWT Security
SECRET_KEY=cloudguard-local-development-secret-key-change-in-production-32chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Local Demo User (Customizable)
DEMO_USER_EMAIL=demo@cloudguard.io
DEMO_USER_PASSWORD=DemoPassword123!
DEMO_USER_NAME=Security Lead
DEMO_WORKSPACE_NAME=Demonstration Workspace
```

---

## 3. Starting the Application

### Backend (FastAPI)

1. Open a terminal in `backend`:
   ```powershell
   cd "backend"
   .\venv\Scripts\python.exe seed.py
   .\venv\Scripts\python.exe run.py
   ```
2. The backend will be available at:
   - API: `http://localhost:8000`
   - OpenAPI Docs: `http://localhost:8000/docs`

### Frontend (React + Vite)

1. Open a terminal in `frontend`:
   ```powershell
   cd "frontend"
   npm run dev
   ```
2. The UI will be available at `http://localhost:5173`.

---

## 4. Demonstration Walkthrough for Professor

### Step 1: Login
- Navigate to `http://localhost:5173/login`.
- Enter the demo credentials:
  - **Email**: `demo@cloudguard.io`
  - **Password**: `DemoPassword123!`
- Notice:
  - Whitespace is automatically stripped and emails are case-insensitive.
  - Entering an incorrect password immediately rejects with HTTP 401.

### Step 2: Demonstration Workspace (Simulated Findings)
- Upon login, the active workspace is **Demonstration Workspace**.
- Notice the clear visual indicators:
  - **Security Overview Score**: 68 / 100 ("Fair").
  - **Demo Notice Banner**: Highlights that findings are deterministic simulated results for offline academic evaluation.
  - **Operational Bar**: Shows `SIMULATED DEMO` status.
- Navigate to **Findings** (`/app/findings`):
  - Review 5 deterministic security findings across S3, EC2, RDS, IAM, and CloudTrail.
  - Each finding shows the amber `Simulated Demo` badge.
  - Clicking a finding opens the detail drawer with the explicit note: *"Simulated Demonstration Finding ... did not originate from a live AWS account"*.
- Navigate to **Scans** (`/app/scans`):
  - View the scan history displaying `Simulated Demo` under the Source column.

### Step 3: Personal Workspace (Real AWS Architecture)
- Click the workspace dropdown in the top header and switch to **Personal Workspace**.
- Notice:
  - The security posture resets to clean slate: *"AWS Not Connected"*.
  - No simulated findings appear in this workspace.
- Navigate to **Settings** (`/app/settings`):
  - Explain the AWS STS `AssumeRole` integration: CloudGuard requires only an IAM Role ARN and External ID.
  - CloudGuard never asks for permanent AWS Access Keys or Secret Keys.
  - When connected to a real AWS account, the scanner discovers live resources and computes the real security score independently.

---

## 5. Verification Commands

To verify all features and tests locally:

```powershell
# 1. Run database migrations
cd backend
.\venv\Scripts\python.exe -m alembic upgrade head

# 2. Run idempotent database seed
.\venv\Scripts\python.exe seed.py

# 3. Run automated demo verification script (9 comprehensive checks)
.\venv\Scripts\python.exe verify_demo.py

# 4. Run backend test suite (113 unit & integration tests)
.\venv\Scripts\python.exe -m pytest

# 5. Build frontend production bundle
cd ..\frontend
npm run build
```
