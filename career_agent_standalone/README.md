# CareerPilot AI — Standalone Job Search & Application Agent v2

CareerPilot is a local-first job-search workspace with an optional background worker. It is independent of GoldMind AI and its databases.

## What this version does

- Searches public web results via Tavily on a schedule and stores job leads.
- Scores leads against the saved career profile/resume.
- Keeps a persistent job pipeline and activity log.
- Supports resume tailoring through optional local Ollama, with a conservative fallback.
- Supports automatic email applications without per-job review **only after you explicitly enable the policy**.
- Enforces application eligibility: job status must be `Verified open`, contact email must be marked verified and have a source URL, match score must meet the configured threshold, resume and signature details must exist, daily application cap must not be reached, and the job must not have a prior application record.
- Records sent/failed/blocked applications and prevents automatic retries of uncertain or previously attempted applications.
- Supports continuous background execution through a separate worker process.

## Important scope limits

Automatic applications currently mean **email applications** to a verified public company/recruitment contact. It does not submit forms to LinkedIn, Naukri, Indeed, WorkIndia, or other portals automatically unless a compliant, supported connector is separately implemented. Portal logins, CAPTCHAs, access controls, and site restrictions are not bypassed. Public search results are leads, not proof that a vacancy is open.

The background discovery process adds new leads as `Needs verification`; it will never automatically send to an unverified search result. Before an email can be sent unattended, you must verify the vacancy, employer/contact, and source URL in the Job Pipeline. This is a one-time job/contact verification, not a per-email review. You explicitly authorise unattended sending in the Autopilot page and set a daily cap.

This software cannot guarantee email delivery, interview outcomes, or vacancy accuracy. SMTP acceptance is recorded as `SENT`, but the recipient's server may still reject or filter the message. Ensure all resume statements are truthful. Never use this to send bulk unsolicited messages; configure modest limits and only apply to relevant roles.

## Install on macOS

```bash
cd career_agent_standalone
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` locally. Configure `TAVILY_API_KEY` for search and SMTP settings for email. Before unattended sending, fill in `CAREER_FULL_NAME`, `CAREER_PHONE`, and `CAREER_EMAIL`. Never share `.env` or commit it to version control.

Start the dashboard:

```bash
streamlit run app.py
```

Open **Profile & Settings**, save your real current resume and career preferences. Under **Job Pipeline**, verify the vacancy is still open, save the public recruitment email and source URL, and check the box confirming that the contact is verified. In **Autopilot**, configure the search interval, match threshold, daily cap, and explicitly enable unattended email applications.

Run the background worker in a second Terminal window (keep the virtual environment activated):

```bash
python worker.py
```

Run one test cycle only:

```bash
python worker.py --once
```

The worker will continue until you stop it with Ctrl+C. The Mac must remain awake and connected to the internet. For true 24/7 operation, run it on an always-on computer/VPS and configure a process supervisor. Keep the dashboard and worker pointed to the same project directory so they use the same SQLite database.

## How unattended sending works

1. Worker searches public job results on the configured interval.
2. New results are saved as unverified leads.
3. It selects only records marked `Verified open` with a verified contact email and contact source URL.
4. It checks match score, resume, sender signature, daily cap, and prior application records.
5. It creates a truthful tailored resume draft (Ollama optional), prepares an application email, and sends the resume as a plain-text attachment.
6. It records the SMTP result and changes the job status to `Applied` if the send call succeeds.

For reliability, the worker reserves an application record before sending. If the process is interrupted during sending, the record may remain `SENDING`; it is not automatically resent because that could duplicate an application. Inspect the Activity Log and your Sent folder before manually resolving it.

## Supported integrations

- Tavily public search API: scheduled job discovery; provider coverage varies.
- Ollama: optional local resume drafting.
- SMTP: email application sending.
- SQLite: local persistent database.

Portal form submissions require a separate supported connector and must respect the portal's terms, login requirements, and automation policy. Do not store portal passwords in this app.
