from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END

from config import settings
from schemas import TriageDecision, ImpactReport, CodeChangePlan
from jira_client import JiraClient
from repo_scanner import list_repo_files, read_selected_files, apply_file_edits, run_test_command
from github_client import GitHubPRClient


class AgentState(TypedDict, total=False):
    ticket_id: str
    mode: str  # "analyze" (Phase 1) or "apply" (Phase 2)
    summary: str
    description: str
    repo_files: list[str]
    code_change_required: bool
    triage_reason: str
    candidate_files: list[str]
    impact_markdown: str
    pr_url: str
    test_passed: bool
    test_output: str
    modified_files: list[str]


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0,
        timeout=30,
        max_retries=1,
    )


def fetch_jira_node(state: AgentState) -> dict:
    jira = JiraClient()
    ticket_id = state["ticket_id"]
    ticket = jira.get_ticket(ticket_id)

    if state["mode"] == "analyze":
        jira.swap_label(ticket_id, remove_label="ai-ready", add_label="ai-analyzing")
    else:
        jira.swap_label(ticket_id, remove_label="ai-approved", add_label="ai-coding")

    return {
        "summary": ticket["summary"],
        "description": ticket["description"],
        "repo_files": list_repo_files("."),
    }


def triage_node(state: AgentState) -> dict:
    llm = _get_llm().with_structured_output(TriageDecision, method="json_schema")
    prompt = f"""You are a senior software engineer triaging a Jira ticket.
Ticket ID: {state['ticket_id']}
Summary: {state['summary']}
Description: {state['description']}

Repository files:
{chr(10).join(state['repo_files'])}

Decide if a repository code change is required to resolve this ticket.
If yes, select up to 8 relevant file paths from the repository list above.
"""
    decision: TriageDecision = llm.invoke(prompt)
    return {
        "code_change_required": decision.code_change_required,
        "triage_reason": decision.reason,
        "candidate_files": decision.candidate_files,
    }


def impact_analysis_node(state: AgentState) -> dict:
    contents = read_selected_files(state.get("candidate_files", []))
    code_context = "\n\n".join(f"=== FILE: {p} ===\n{c}" for p, c in contents.items())

    llm = _get_llm().with_structured_output(ImpactReport, method="json_schema")
    prompt = f"""You are a principal software architect performing a pre-change impact analysis.
Ticket ID: {state['ticket_id']}
Summary: {state['summary']}
Description: {state['description']}

Relevant Source Code:
{code_context}

List the exact files/functions to modify, all downstream impacts, risk level, edge cases, and a step-by-step plan.
"""
    report: ImpactReport = llm.invoke(prompt)

    files_bullets = "\n".join(f"- {item}" for item in report.files_to_change) or "- None"
    impact_bullets = "\n".join(f"- {item}" for item in report.downstream_impacts) or "- None identified"
    edge_bullets = "\n".join(f"- {item}" for item in report.edge_cases) or "- None noted"

    md = (
        f"## AI Impact Analysis — {state['ticket_id']}\n\n"
        f"**Risk Level:** {report.risk_level}\n\n"
        f"### Files to Change\n{files_bullets}\n\n"
        f"### Downstream Impact\n{impact_bullets}\n\n"
        f"### Edge Cases & Risks\n{edge_bullets}\n\n"
        f"### Implementation Plan\n{report.implementation_plan}\n\n"
        f"---\n"
        f"Add the label `ai-approved` to this Jira ticket to generate an automated Draft PR."
    )
    return {"impact_markdown": md}


def post_analysis_node(state: AgentState) -> dict:
    jira = JiraClient()
    ticket_id = state["ticket_id"]

    if not state.get("code_change_required"):
        msg = (
            f"AI Triage ({ticket_id}): No code change required.\n\n"
            f"Reason: {state.get('triage_reason', 'N/A')}"
        )
        jira.add_comment(ticket_id, msg)
        jira.swap_label(ticket_id, remove_label="ai-analyzing", add_label="no-code-change")
    else:
        jira.add_comment(ticket_id, state["impact_markdown"])
        jira.swap_label(ticket_id, remove_label="ai-analyzing", add_label="ai-awaiting-approval")
    return {}


def generate_and_apply_code_node(state: AgentState) -> dict:
    contents = read_selected_files(state.get("candidate_files", []))
    code_context = "\n\n".join(f"=== FILE: {p} ===\n{c}" for p, c in contents.items())

    llm = _get_llm().with_structured_output(CodeChangePlan, method="json_schema")
    prompt = f"""You are a senior software engineer implementing a Jira ticket.
Ticket ID: {state['ticket_id']}
Summary: {state['summary']}
Description: {state['description']}

Approved Impact Analysis:
{state['impact_markdown']}

Current Source Code:
{code_context}

Return the complete updated content for every file that needs modification.
Keep changes minimal, clean, and production-ready. Never omit existing code with placeholders.
"""
    plan: CodeChangePlan = llm.invoke(prompt)
    modified_files = apply_file_edits(plan.edits, repo_root=".")
    passed, test_output = run_test_command(settings.test_command, repo_root=".")

    branch_name = f"ai/{state['ticket_id'].lower()}-{plan.branch_slug[:30]}"
    changes_summary = "\n".join(
        f"- `{e.file_path}`: {e.summary_of_change}" for e in plan.edits
    )
    test_badge = "PASSED" if passed else "FAILED (Review Required)"
    pr_body = (
        f"## Jira Ticket\n"
        f"- **ID:** {state['ticket_id']}\n"
        f"- **Summary:** {state['summary']}\n\n"
        f"## Files Changed\n{changes_summary}\n\n"
        f"{state['impact_markdown']}\n\n"
        f"## Automated Test Result: {test_badge}\n"
        f"```text\n{test_output}\n```\n"
    )

    gh = GitHubPRClient()
    gh.create_branch_commit_and_push(
        branch_name=branch_name,
        commit_message=plan.commit_message,
        modified_files=modified_files,
        cwd=".",
    )
    pr_url = gh.open_draft_pr(
        title=plan.pr_title,
        body=pr_body,
        head_branch=branch_name,
    )

    jira = JiraClient()
    jira.add_comment(
        state["ticket_id"],
        f"AI Draft PR created for {state['ticket_id']}: {pr_url}\n\nTest Status: {test_badge}",
    )
    jira.swap_label(state["ticket_id"], remove_label="ai-coding", add_label="ai-pr-created")

    return {
        "pr_url": pr_url,
        "test_passed": passed,
        "test_output": test_output,
        "modified_files": modified_files,
    }


def route_after_triage(state: AgentState) -> str:
    if not state.get("code_change_required"):
        return "post_analysis"
    return "impact_analysis"


def route_after_impact(state: AgentState) -> str:
    if state.get("mode") == "apply":
        return "apply_and_pr"
    return "post_analysis"


def build_agent_graph():
    builder = StateGraph(AgentState)
    builder.add_node("fetch_jira", fetch_jira_node)
    builder.add_node("triage", triage_node)
    builder.add_node("impact_analysis", impact_analysis_node)
    builder.add_node("post_analysis", post_analysis_node)
    builder.add_node("apply_and_pr", generate_and_apply_code_node)

    builder.add_edge(START, "fetch_jira")
    builder.add_edge("fetch_jira", "triage")
    builder.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "impact_analysis": "impact_analysis",
            "post_analysis": "post_analysis",
        },
    )
    builder.add_conditional_edges(
        "impact_analysis",
        route_after_impact,
        {
            "post_analysis": "post_analysis",
            "apply_and_pr": "apply_and_pr",
        },
    )
    builder.add_edge("post_analysis", END)
    builder.add_edge("apply_and_pr", END)
    return builder.compile()
