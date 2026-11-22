import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    jira_base_url: str = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    jira_email: str = os.getenv("JIRA_EMAIL", "")
    jira_api_token: str = os.getenv("JIRA_API_TOKEN", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_repository: str = os.getenv("GITHUB_REPOSITORY", "")
    github_base_branch: str = os.getenv("GITHUB_BASE_BRANCH", "main")
    test_command: str = os.getenv("TEST_COMMAND", "").strip()
    jira_project_key: str = os.getenv("JIRA_PROJECT_KEY", "")

    def validate_phase1(self) -> None:
        missing = [
            name
            for name, val in [
                ("GOOGLE_API_KEY", self.google_api_key),
                ("JIRA_BASE_URL", self.jira_base_url),
                ("JIRA_EMAIL", self.jira_email),
                ("JIRA_API_TOKEN", self.jira_api_token),
            ]
            if not val
        ]
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

    def validate_phase2(self) -> None:
        self.validate_phase1()
        missing = [
            name
            for name, val in [
                ("GITHUB_TOKEN", self.github_token),
                ("GITHUB_REPOSITORY", self.github_repository),
            ]
            if not val
        ]
        if missing:
            raise EnvironmentError(f"Missing required GitHub variables for Phase 2: {', '.join(missing)}")


settings = Settings()
