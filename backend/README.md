# CloudGuard

CloudGuard is an AWS cloud security scanner. Know what's exposed. Secure what's critical.

## Backend

The CloudGuard backend is a FastAPI application that will eventually:
- Connect securely to an AWS environment.
- Discover AWS resources.
- Analyze their security configurations against predefined rules.
- Detect misconfigurations and assign severities.
- Calculate a security score.
- Expose results through REST APIs to the React frontend.

## Current Part (Part 1)

This current implementation is **Part 1**, which establishes the backend foundation. 
It contains the scalable architecture, configuration management, structured logging, basic routing, and error handling, but does not yet connect to AWS or a PostgreSQL database.

## Tech Stack

- **Python 3.12+**
- **FastAPI**
- **Uvicorn**
- **Pydantic**
- **pytest**

## Setup

Follow these beginner-friendly steps to run the backend locally:

1. **Create virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   ```
   Activate it:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   Create a `.env` file from the example:
   - On Windows (PowerShell): `Copy-Item .env.example .env`
   - On macOS/Linux: `cp .env.example .env`

4. **Start FastAPI server:**
   ```bash
   python run.py
   ```

5. **View API Documentation:**
   Open your browser and navigate to:
   [http://localhost:8000/docs](http://localhost:8000/docs)

## AWS Connection

CloudGuard does not directly store a user's AWS password or long-term secrets in the database or frontend.
Instead, we use a secure assume-role pattern:
1. User creates a read-only IAM Role in their AWS account.
2. CloudGuard receives the Role ARN.
3. Backend requests AWS STS `AssumeRole`.
4. AWS returns temporary, short-lived credentials.
5. CloudGuard uses those credentials to verify the account and create a session.
6. Future scanners use that temporary session.

This pattern is much safer than transmitting or storing permanent AWS access keys.

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/aws/connect \
-H "Content-Type: application/json" \
-d '{
"role_arn": "arn:aws:iam::123456789012:role/CloudGuardScannerRole",
"region": "ap-south-1"
}'
```

**Expected Safe Response:**
```json
{
  "connected": true,
  "account_id": "123456789012",
  "region": "ap-south-1",
  "identity_arn": "arn:aws:sts::123456789012:assumed-role/CloudGuardScannerRole/cloudguard-security-scan",
  "message": "AWS account connected successfully"
}
```
*(Notice that no credentials are returned in the response)*

## Resource Discovery

After a successful AWS connection, you can trigger resource discovery. The backend securely uses the active connection to fetch the inventory of various AWS resources without performing any security scans. 
Supported services:
- S3
- EC2 (Instances, Security Groups)
- IAM (Users, Roles)
- RDS
- CloudTrail

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/discovery/run
```
*(Returns a JSON representation of the `ResourceInventory` schema containing all discovered assets)*

## Security Scanner & Rule Engine

CloudGuard analyzes the discovered AWS resources against predefined security rules using its scalable Rule Engine. It uses a strict architecture ensuring that resource discovery logic is separated from security evaluation.

**Scan Process (`POST /api/v1/scans`):**
1. **Discovery**: Fetches the latest inventory via the active connection.
2. **Scanner**: Individual service scanners prepare relevant configurations without mutating AWS (e.g., checking if S3 encryption is enabled).
3. **Rules**: The `RuleEngine` evaluates 11 built-in rules (such as `S3_PUBLIC_ACCESS`, `EC2_PUBLIC_IP`, `SSH_OPEN_TO_WORLD`) across the prepared data.
4. **Findings**: Generated findings (CRITICAL, HIGH, MEDIUM, LOW) are returned dynamically.

### Example Scan Trigger

```bash
curl -X POST http://localhost:8000/api/v1/scans
```

**Expected Result Snippet:**
```json
{
  "scan_id": "8b7...19a",
  "status": "completed",
  "account_id": "123456789012",
  "summary": {
    "resources_scanned": 15,
    "findings": 4,
    "critical": 1,
    "high": 2,
    "medium": 1,
    "low": 0
  },
  "findings": [
    {
      "finding_id": "...",
      "rule_id": "SSH_OPEN_TO_WORLD",
      "title": "Security group allows unrestricted SSH access",
      "severity": "CRITICAL",
      ...
    }
  ]
}
```
## Risk Engine & Security Score

After scanning, CloudGuard evaluates how dangerous findings are using a deterministic **Risk Engine**.

### 1. Finding Risk Scores (0-100)
A finding like "SSH exposed to internet" is mapped to a `CRITICAL` severity (base score 90). The Risk Engine adds contextual modifiers (e.g. +5 for Internet exposure) to produce a `risk_score` (e.g. 95) and assigns a priority (`P1`). 

### 2. Overall Security Score (0-100)
CloudGuard starts with a perfect score of 100.
Security findings subtract from this score based on severity penalties:
* CRITICAL: -10 points
* HIGH: -6 points
* MEDIUM: -3 points
* LOW: -1 point

**Caps:** Penalties are capped per severity (e.g. max -40 points for Criticals). This ensures a single misconfigured auto-scaling group doesn't unfairly drag the entire account score to 0. The final result represents a highly accurate view of your overall security posture.

### Example Dashboard Trigger

```bash
curl -X GET http://localhost:8000/api/v1/dashboard
```

**Expected Result Snippet:**
```json
{
  "security_score": 72,
  "rating": "Needs Attention",
  "category_scores": {
    "NETWORK": {
      "score": 84,
      "findings": 2,
      ...
    }
  },
  "top_risks": [
    {
      "title": "Security group allows unrestricted SSH access",
      "risk_score": 95,
      "priority": "P1"
    }
  ]
}
```
Findings can be queried via `GET /api/v1/scans/findings`.

