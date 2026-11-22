# Jira-to-GitHub-PR AI Agent (LangGraph + Gemini + GitHub Actions)

An automated AI agent that reads Jira tickets, tags them to prevent duplicate runs, inspects your codebase, lists all files to change + downstream impact, and opens a **Draft Pull Request** on GitHub with structured comments after human approval.

## Workflow Overview

1. **Phase 1 (`--mode analyze`)**:
   - Reads the Jira ticket and swaps label `ai-ready` -> `ai-analyzing`.
   - Scans repository files and decides if a code change is required.
   - If **no code change** is needed: posts explanation on Jira and tags `no-code-change`.
   - If **code change is required**: posts a full Impact Analysis (files, downstream impact, risk level, edge cases, plan) to Jira and tags `ai-awaiting-approval`.
2. **Phase 2 (`--mode apply`)**:
   - Triggered when a human adds the label `ai-approved` (or runs manually).
   - Swaps `ai-approved` -> `ai-coding`, edits the code, optionally runs `TEST_COMMAND`, pushes a branch (`ai/<ticket-id>-...`), opens a **Draft PR** on GitHub, and posts the PR link back to Jira with label `ai-pr-created`.

---

## 1. Local Quick Start (5 Minutes)

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r ai_agent/requirements.txt

cp .env.example .env
# Fill in GOOGLE_API_KEY, JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
```

Run Phase 1 (Read-Only Impact Analysis) on a test ticket:
```bash
python ai_agent/main.py --ticket PROJ-101 --mode analyze
```

Run Phase 2 (Code Edit + Auto Draft PR):
```bash
python ai_agent/main.py --ticket PROJ-101 --mode apply
```

---

## 2. Continuous 24/7 Setup on GitHub Actions ($0/month)

1. Copy the `ai_agent/` and `.github/` folders into your GitHub repository.
2. In GitHub, go to **Settings -> Secrets and variables -> Actions -> Secrets** and add:
   - `GOOGLE_API_KEY` (from Google AI Studio)
   - `JIRA_BASE_URL` (e.g., `https://yourteam.atlassian.net`)
   - `JIRA_EMAIL` (your Jira login email)
   - `JIRA_API_TOKEN` (from Atlassian Account Security)
3. *(Optional)* Under **Variables**, add:
   - `TEST_COMMAND` (e.g., `pytest`, `mvn test`, or `npm test`)
   - `JIRA_PROJECT_KEY` (only needed if using Cron polling)
4. Test immediately from the **Actions** tab -> **Jira-to-PR AI Agent** -> **Run workflow**.

### Triggering Automatically from Jira
Choose either:
- **Option A (Instant — Jira Automation):** Create a Jira Automation rule when label `ai-ready` is added -> *Send web request* (`POST`) to `https://api.github.com/repos/YOUR_USER/YOUR_REPO/dispatches` with header `Authorization: Bearer YOUR_GITHUB_PAT` and JSON body:
  ```json
  {
    "event_type": "jira-ticket-ready",
    "client_payload": { "ticket_id": "{{issue.key}}" }
  }
  ```
  *(Repeat with `event_type: "jira-ticket-approved"` for label `ai-approved`.)*
- **Option B (100% Free Unlimited — Cron Poller):** Open `.github/workflows/jira-agent-cron.yml` and uncomment the `schedule` block so GitHub checks Jira every 15 minutes without using Jira Automation steps.
