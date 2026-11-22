import requests
from requests.auth import HTTPBasicAuth
from config import settings


class JiraClient:
    def __init__(self):
        self.base_url = settings.jira_base_url
        self.auth = HTTPBasicAuth(settings.jira_email, settings.jira_api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_ticket(self, ticket_id: str) -> dict:
        url = f"{self.base_url}/rest/api/3/issue/{ticket_id}"
        res = requests.get(url, headers=self.headers, auth=self.auth, timeout=20)
        res.raise_for_status()
        fields = res.json().get("fields", {})
        return {
            "id": ticket_id,
            "summary": fields.get("summary", ""),
            "description": self._extract_text(fields.get("description")),
            "labels": fields.get("labels", []),
            "status": (fields.get("status") or {}).get("name", ""),
        }

    def search_tickets_by_label(self, label: str, project_key: str = "") -> list[str]:
        jql = f'labels = "{label}"'
        if project_key:
            jql = f'project = "{project_key}" AND {jql}'
        url = f"{self.base_url}/rest/api/3/search/jql"
        payload = {"jql": jql, "fields": ["key"], "maxResults": 10}
        res = requests.post(url, json=payload, headers=self.headers, auth=self.auth, timeout=20)
        res.raise_for_status()
        issues = res.json().get("issues", [])
        return [issue["key"] for issue in issues if "key" in issue]

    def swap_label(self, ticket_id: str, remove_label: str | None, add_label: str | None) -> None:
        url = f"{self.base_url}/rest/api/3/issue/{ticket_id}"
        label_ops = []
        if remove_label:
            label_ops.append({"remove": remove_label})
        if add_label:
            label_ops.append({"add": add_label})
        if not label_ops:
            return
        payload = {"update": {"labels": label_ops}}
        res = requests.put(url, json=payload, headers=self.headers, auth=self.auth, timeout=20)
        res.raise_for_status()

    def add_comment(self, ticket_id: str, text: str) -> None:
        url = f"{self.base_url}/rest/api/3/issue/{ticket_id}/comment"
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        content_nodes = [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": para}],
            }
            for para in paragraphs
        ]
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": content_nodes or [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
            }
        }
        res = requests.post(url, json=payload, headers=self.headers, auth=self.auth, timeout=20)
        res.raise_for_status()

    def _extract_text(self, adf_node) -> str:
        if not adf_node:
            return ""
        if isinstance(adf_node, str):
            return adf_node
        if adf_node.get("type") == "text":
            return adf_node.get("text", "")
        parts = [self._extract_text(child) for child in adf_node.get("content", [])]
        return " ".join(p for p in parts if p).strip()
