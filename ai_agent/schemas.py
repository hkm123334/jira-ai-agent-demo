from pydantic import BaseModel, Field


class TriageDecision(BaseModel):
    code_change_required: bool = Field(
        description="True if repository code changes are required to resolve this Jira ticket."
    )
    reason: str = Field(
        description="Clear, concise explanation of why code changes are or are not required."
    )
    candidate_files: list[str] = Field(
        default_factory=list,
        description="Up to 8 exact file paths from the repository file list that should be inspected.",
    )


class ImpactReport(BaseModel):
    files_to_change: list[str] = Field(
        description="Exact file paths and functions/classes/methods that must be modified."
    )
    downstream_impacts: list[str] = Field(
        description="Affected APIs, callers, database queries, shared utilities, configs, or unit tests."
    )
    risk_level: str = Field(
        description="Overall risk level: LOW, MEDIUM, or HIGH."
    )
    edge_cases: list[str] = Field(
        default_factory=list,
        description="Potential edge cases or regression risks to watch during review.",
    )
    implementation_plan: str = Field(
        description="Step-by-step summary of the code changes required."
    )


class FileEdit(BaseModel):
    file_path: str = Field(
        description="Relative path to the file in the repository to modify or create."
    )
    summary_of_change: str = Field(
        description="Short 1-sentence description of what changed in this file."
    )
    updated_content: str = Field(
        description="Complete updated file content (never use placeholders like '# ... rest of file')."
    )


class CodeChangePlan(BaseModel):
    branch_slug: str = Field(
        description="Short kebab-case slug for the git branch name (e.g., fix-null-discount)."
    )
    commit_message: str = Field(
        description="Concise conventional commit message including the Jira ticket ID."
    )
    pr_title: str = Field(
        description="Pull Request title starting with [TICKET-ID]."
    )
    edits: list[FileEdit] = Field(
        description="List of file edits to apply."
    )
