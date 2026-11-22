import argparse
from config import settings
from graph import build_agent_graph


def main():
    parser = argparse.ArgumentParser(description="Jira-to-GitHub-PR AI Agent")
    parser.add_argument("--ticket", required=True, help="Jira Ticket ID (e.g., PROJ-101)")
    parser.add_argument(
        "--mode",
        choices=["analyze", "apply"],
        default="analyze",
        help="analyze = Phase 1 read-only impact report; apply = Phase 2 code edit + Draft PR",
    )
    args = parser.parse_args()

    if args.mode == "apply":
        settings.validate_phase2()
    else:
        settings.validate_phase1()

    graph = build_agent_graph()
    result = graph.invoke({"ticket_id": args.ticket, "mode": args.mode})

    print(f"[DONE] Ticket: {args.ticket} | Mode: {args.mode}")
    if result.get("pr_url"):
        print(f"[PR CREATED] {result['pr_url']}")


if __name__ == "__main__":
    main()
