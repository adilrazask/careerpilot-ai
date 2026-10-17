# CareerPilot AI

**Autonomous Job Discovery, Resume Intelligence, Application Automation and HR Outreach Platform**

CareerPilot AI is a production-grade, autonomous recruitment employee platform engineered to replace the tedious manual job-hunting workflow. It operates continuously in the background to discover vacancies, score candidate-job fit with transparent multi-factor analytics, generate 100% truthful tailored ATS resumes and cover letters, discover and verify recruiter contacts, submit approved applications via email or portals, monitor recruiter replies, and manage follow-ups.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |       React + Vite Frontend SPA       |
                      |   (TypeScript, Tailwind CSS, Lucide)  |
                      |         http://localhost:5173         |
                      +-------------------+-------------------+
                                          | REST API / JSON
                                          v
                      +---------------------------------------+
                      |         FastAPI Backend Server        |
                      |   (Pydantic v2, CORS, Starlette)      |
                      |         http://localhost:8000         |
                      +---------+-------------------+---------+
                                |                   |
                 Database Ops   |                   | Lease & Heartbeat
                                v                   v
            +---------------------------+   +---------------------------+
            |      SQLAlchemy ORM       |   | Durable Background Worker |
            |    (SQLite / Postgres)    |<--|     (Standalone Script)   |
            |        34 Models          |   |  Lease Lock & Heartbeat   |
            +---------------------------+   +---------------------------+
                                |
       +------------------------+------------------------+
       |                        |                        |
       v                        v                        v
+--------------+       +------------------+     +------------------+
|  Matching    |       | Resume Tailoring |     | Outreach Engine  |
|  Engine      |       |  & Document Gen  |     | DNS Verification |
| (Multi-factor|       | (PDF & DOCX ATS) |     |  IMAP Poller     |
+--------------+       +------------------+     +------------------+
```

---

## Key System Capabilities

### 1. Transparent Multi-Factor Matching Engine
- **Title Alignment (25 pts)**: Strict job family matching (Operations, Procurement, Logistics, ERP/CRM).
- **Skill Keyword & Domain Overlap (35 pts)**: Maps mandatory vs. preferred skills against candidate facts.
- **Experience Requirement Fit (20 pts)**: Penalizes roles requiring far more or less experience than candidate's profile.
- **Location & Work Mode (10 pts)**: Evaluates primary location (Hyderabad), remote options, and relocation preferences.
- **Salary Compatibility (10 pts)**: Compares stated salary range against candidate expectations.
- **Honest Classifications**: `LIKELY_ELIGIBLE` (score >= 70), `REVIEW_REQUIRED` (50–69), `NOT_ELIGIBLE` (< 50 or excluded company/misaligned requirements).

### 2. Truthful Resume & Document Intelligence
- **Zero Hallucination Guarantee**: Does not invent employers, degrees, certifications, job titles, or dates.
- **ATS Reordering & Highlight**: Re-prioritizes genuine bullet points and highlights matching skills without altering factual meaning.
- **Dual Document Generation**: Automatically builds ATS-compliant **PDF** (via ReportLab Flowables) and **DOCX** (via `python-docx`).
- **Tailored Cover Letters**: Contextual application cover letters generated from candidate facts.

### 3. Contact Discovery & Verification Pipeline
- **Multi-Stage Validation**:
  - RFC 5322 syntax validation.
  - Live domain DNS and MX mail-exchanger verification.
  - Official public source URL verification (e.g. company team page or careers directory).
- **Strict Anti-Guessing Guard**: Rejects generic inboxes (`info@`, `careers@`, `sales@`) and unverified patterns.
- **States**: `DISCOVERED`, `SOURCE_VERIFIED`, `EMAIL_VALIDATED`, `UNVERIFIED`, `INVALID`.

### 4. Outbound Email Outreach & Inbound Response Classifier
- **Idempotency Keys**: Generates unique keys (`APP-{id}-INITIAL_OUTREACH`) to prevent duplicate email transmissions.
- **Sandbox Fallback**: Safe mock delivery when SMTP credentials are not configured, enabling zero-risk local testing.
- **Inbound IMAP Poller**: Automatically fetches and classifies recruiter responses:
  - `INTERVIEW_INVITATION` (Triggers pipeline progression and cancels follow-ups).
  - `OFFER` (Flags for human review; **never auto-accepts**).
  - `REJECTION` (Marks application status and logs rejection).
  - `SUSPICIOUS` (Detects fee requests, crypto scams, or unofficial channels).

### 5. Durable Background Worker & Lease Queue
- Independent process running separately from the browser.
- **Heartbeat & Liveness**: Live timestamp registry; UI displays offline warnings if worker dies.
- **Lease Locks & Crash Recovery**: Tasks locked with time-bounded leases; expired leases automatically reconciled to `RETRYING`.
- **Anti-Duplication**: In-flight applications are safely reconciled without blind retries.

### 6. Interactive 10-Screen Frontend Dashboard
- **Main Dashboard**: Live KPIs, conversion funnel chart, worker health indicator, emergency stop.
- **AI Agent Workspace**: Conversational objective interface; parses natural-language prompts into structured filters and multi-portal search plans.
- **Job Discovery**: Multi-portal filterable vacancy table, detailed inspection modal, manual vacancy addition.
- **Career Profile**: Editable factual claims ledger, resume uploader, skills and experience editor.
- **Resume Intelligence**: Tailored resume and cover letter inspector, real-time PDF and DOCX download buttons.
- **Contact Discovery**: Recruiter directory with live verification triggers and confidence scores.
- **Application Pipeline**: 21-state ATS tracking table with delivery evidence view and manual state transitions.
- **Integrations**: Marketplace for Ollama, SMTP, IMAP, Tavily Search, LinkedIn, and Naukri with live test handshakes.
- **Autopilot Policy**: Controls for unattended applications, daily volume caps, minimum score thresholds, and excluded employers.
- **Audit Logs**: Immutable system activity trail, security logs, and integration health metrics.

---

## Quick Start Guide

### Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Node.js 18+ and npm

### 1. Clone & Setup
```bash
cd /Users/adilraja/.gemini/antigravity/scratch/careerpilot-ai
./start.sh
```

### 2. Start Services

Open three separate terminal windows:

#### Terminal 1: Backend API
```bash
cd backend
./run_backend.sh
# Server running at: http://127.0.0.1:8000
# OpenAPI Documentation: http://127.0.0.1:8000/docs
```

#### Terminal 2: Durable Background Worker
```bash
cd backend
./run_worker.sh
# Worker running with live heartbeat monitoring
```

#### Terminal 3: Frontend Dashboard
```bash
cd frontend
./run_frontend.sh
# Dashboard active at: http://localhost:5173
```

---

## Running the Automated Test Suite

CareerPilot AI includes unit tests, API integration tests, and a complete 18-step end-to-end workflow verification test.

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest tests/ -v
```

### Test Results (22 passed, 100% success):
- `test_health_check`: Backend health endpoint sanity check.
- `test_dashboard_metrics`: Live KPI and worker state query.
- `test_profile_endpoints`: Profile retrieval and factual updates.
- `test_job_and_tailoring_pipeline`: Manual job listing creation and resume tailoring.
- `test_agent_workspace_instruction`: Natural-language objective interpretation.
- `test_integrations_list_and_test`: Integration registry and test handshakes.
- `test_audit_logs`: Audit trail persistence.
- `test_profile_initialization`: Seed data and career profile validation.
- `test_canonicalize_url_strips_tracking`: Strips UTM parameters and tracking tags.
- `test_normalize_title`: Normalizes job titles for deduplication.
- `test_duplicate_detection`: Filters duplicate listings.
- `test_job_matching_high_fit`: Multi-factor scoring on suitable role.
- `test_job_matching_excluded_company`: Enforces employer exclusion policy.
- `test_contact_verification_rejects_invalid_syntax`: Rejects invalid email syntax.
- `test_contact_verification_rejects_guesses`: Anti-guessing regex blocks placeholder addresses.
- `test_resume_tailoring_truthfulness`: Validates 100% factual consistency score.
- `test_document_generation`: ATS PDF and DOCX document builder.
- `test_recruiter_email_classification`: Inbound message intent classifier.
- `test_application_idempotency`: Prevents duplicate email outreach.
- `test_follow_up_cancellation_on_reply`: Automatically cancels follow-ups when recruiter replies.
- `test_audit_log_persistence`: Validates audit log records.
- `test_complete_18_step_autonomous_workflow`: Full 18-step verification from candidate profile loading to dashboard update.

---

## Configuration & Environment Variables

Create or edit `backend/.env`:

```ini
# Application Mode
DEBUG=True
DATABASE_URL=sqlite:///./data/careerpilot.db

# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:latest

# Email Integration (Outbound SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com

# Email Integration (Inbound IMAP)
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your_email@gmail.com
IMAP_PASSWORD=your_app_password

# Search Integration
TAVILY_API_KEY=your_tavily_key_here
```

*Note: If SMTP/IMAP credentials are not provided or set to mock defaults, CareerPilot AI safely executes in sandbox mode without failing.*

---

## System Safety & Governance Guarantees

1. **Never Invent Qualifications**: Skills, employers, metrics, and dates are strictly sourced from verified candidate profile facts.
2. **Never Guessed Addresses**: Applications are only dispatched to contacts verified via DNS/MX and authentic public sources.
3. **Never Auto-Accept Offers**: Job offers and employment contracts are permanently flagged for human owner review and decision.
4. **Idempotency Locks**: Duplicate outreach emails are physically blocked at the database level by unique idempotency keys.
5. **Anti-Bot Compliance**: Portal automation detects CAPTCHAs and security checks, automatically pausing and notifying the owner.
