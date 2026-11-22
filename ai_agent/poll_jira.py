"""
Optional Cron Poller (100% Free — bypasses Jira Automation step limits).
Checks Jira for tickets labeled 'ai-ready' (Phase 1) and 'ai-approved' (Phase 2).
"""
from config import settings
from jira_client import JiraClient
from graph import build_agent_graph


def run_poll():
    settings.validate_phase1()
    jira = JiraClient()
    graph = build_agent_graph()

    # 1. Process new tickets awaiting impact analysis
    ready_tickets = jira.search_tickets_by_label("ai-ready", settings.jira_project_key)
    for ticket_id in ready_tickets:
        print(f"[POLL] Analyzing ticket: {ticket_id}")
        graph.invoke({"ticket_id": ticket_id, "mode": "analyze"})

    # 2. Process human-approved tickets for Draft PR generation
    if settings.github_token and settings.github_repository:
        approved_tickets = jira.search_tickets_by_label("ai-approved", settings.jira_project_key)
        for ticket_id in approved_tickets:
            print(f"[POLL] Applying changes & opening PR for: {ticket_id}")
            graph.invoke({"ticket_id": ticket_id, "mode": "apply"})


if __name__ == "__main__":
    run_poll()
