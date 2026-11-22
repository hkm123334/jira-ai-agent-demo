import subprocess
from pathlib import Path

IGNORE_DIRS = {
    ".git",
    ".github",
    "node_modules",
    "target",
    "build",
    "dist",
    "__pycache__",
    ".venv",
    "venv",
    "ai_agent",
}

ALLOWED_EXTS = {
    ".py", ".java", ".kt", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".rs", ".rb", ".php", ".cs", ".cpp", ".c", ".h",
    ".yml", ".yaml", ".json", ".xml", ".sql", ".properties", ".toml", ".html", ".css",
}


def list_repo_files(repo_root: str = ".", max_files: int = 300) -> list[str]:
    root = Path(repo_root).resolve()
    files = []
    for path in root.rglob("*"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTS:
            files.append(path.relative_to(root).as_posix())
    return sorted(files)[:max_files]


def read_selected_files(
    file_paths: list[str],
    repo_root: str = ".",
    max_files: int = 10,
    max_chars_per_file: int = 12000,
) -> dict[str, str]:
    root = Path(repo_root).resolve()
    contents = {}
    for rel_path in file_paths[:max_files]:
        target = (root / rel_path).resolve()
        if not str(target).startswith(str(root)):
            continue
        if target.is_file():
            text = target.read_text(encoding="utf-8", errors="ignore")
            contents[rel_path] = text[:max_chars_per_file]
    return contents


def apply_file_edits(edits: list, repo_root: str = ".") -> list[str]:
    root = Path(repo_root).resolve()
    modified = []
    for edit in edits:
        target = (root / edit.file_path).resolve()
        if not str(target).startswith(str(root)):
            raise ValueError(f"Refusing to write outside repository root: {edit.file_path}")
        if any(part in IGNORE_DIRS for part in Path(edit.file_path).parts):
            raise ValueError(f"Refusing to modify protected directory: {edit.file_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(edit.updated_content, encoding="utf-8")
        modified.append(edit.file_path)
    return modified


def run_test_command(command: str, repo_root: str = ".") -> tuple[bool, str]:
    if not command:
        return True, "No TEST_COMMAND configured; skipped automated tests."
    result = subprocess.run(
        command,
        cwd=repo_root,
        shell=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, output[-4000:]
