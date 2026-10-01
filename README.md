# CloudGuard

**Know what's exposed. Secure what's critical.**

CloudGuard is an AWS cloud security scanner that connects to your AWS environment, discovers resources, analyzes their security configurations, and provides a comprehensive security score.

## Project Structure

```
cloudguard/
├── frontend/          # React + Vite + Tailwind UI
│   ├── src/           # Components, pages, hooks, context
│   ├── public/        # Static assets
│   └── ...            # Vite/TS/Tailwind configs
├── backend/           # FastAPI + Python backend
│   ├── app/           # Core application (API, scanners, rules, risk engine)
│   ├── tests/         # pytest test suite
│   └── ...            # Requirements, Alembic migrations
└── docs/              # Shared documentation
```

## Getting Started

### Backend (FastAPI)

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Backend runs at: [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: [http://localhost:5173](http://localhost:5173)

## Features

- **Secure AWS Connection** — Uses IAM AssumeRole, no long-term credentials stored
- **Resource Discovery** — S3, EC2, IAM, RDS, CloudTrail
- **Security Scanner** — 11 built-in rules (S3 public access, SSH open to world, etc.)
- **Risk Engine** — Severity-based scoring with contextual modifiers
- **Security Score** — 0-100 overall score with per-category breakdown
- **Dashboard** — Real-time security posture overview

## Tech Stack

| Layer    | Tech                                      |
|----------|-------------------------------------------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS  |
| Backend  | Python 3.12+, FastAPI, Uvicorn, Pydantic  |
| Testing  | pytest                                    |
