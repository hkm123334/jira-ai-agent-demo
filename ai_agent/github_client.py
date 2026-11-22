import subprocess
from github import Github, Auth
from config import settings


class GitHubPRClient:
    def __init__(self):
        auth = Auth.Token(settings.github_token)
        self.gh = Github(auth=auth)
        self.repo = self.gh.get_repo(settings.github_repository)

    def _run_git(self, args: list[str], cwd: str = ".") -> str:
        res = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()

    def create_branch_commit_and_push(
        self,
        branch_name: str,
        commit_message: str,
        modified_files: list[str],
        cwd: str = ".",
    ) -> None:
        self._run_git(["config", "user.name", "jira-ai-agent[bot]"], cwd=cwd)
        self._run_git(["config", "user.email", "jira-ai-agent@users.noreply.github.com"], cwd=cwd)
        self._run_git(["checkout", "-B", branch_name], cwd=cwd)
        self._run_git(["add", *modified_files], cwd=cwd)
        self._run_git(["commit", "-m", commit_message], cwd=cwd)
        self._run_git(["push", "--force-with-lease", "-u", "origin", branch_name], cwd=cwd)

    def open_draft_pr(self, title: str, body: str, head_branch: str) -> str:
        pr = self.repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=settings.github_base_branch,
            draft=True,
        )
        return pr.html_url
