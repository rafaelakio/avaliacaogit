"""GitHub API data collector."""

import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import requests

from .config import GITHUB_API_BASE, MAX_COMMITS, COMMITS_PER_PAGE


@dataclass
class CommitInfo:
    sha: str
    message: str
    date: Optional[str]
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0
    author: str = ""


@dataclass
class RepoData:
    owner: str
    repo: str
    full_name: str
    description: Optional[str]
    language: Optional[str]
    languages: dict[str, int] = field(default_factory=dict)
    size_kb: int = 0
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    created_at: Optional[str] = None
    pushed_at: Optional[str] = None
    default_branch: str = "main"
    topics: list[str] = field(default_factory=list)
    commits: list[CommitInfo] = field(default_factory=list)
    branches: list[str] = field(default_factory=list)
    open_prs: int = 0
    closed_prs: int = 0
    merged_prs: int = 0
    open_issues_count: int = 0
    closed_issues_count: int = 0
    root_files: list[str] = field(default_factory=list)
    root_dirs: list[str] = field(default_factory=list)
    all_paths: list[str] = field(default_factory=list)
    readme_content: str = ""
    readme_length: int = 0
    dependency_content: dict[str, str] = field(default_factory=dict)
    has_ci_cd: bool = False
    ci_cd_files: list[str] = field(default_factory=list)
    has_dockerfile: bool = False
    has_tests: bool = False
    test_files_count: int = 0
    quality_files: list[str] = field(default_factory=list)
    has_license: bool = False
    has_gitignore: bool = False
    contributor_count: int = 1
    error: Optional[str] = None


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub repository URL."""
    url = url.strip().rstrip("/")
    m = re.search(r"github\.com[/:]([^/]+)/([^/\s.]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    # Detect user profile URL and provide a helpful error
    profile = re.search(r"github\.com[/:]([^/\s]+)$", url)
    if profile:
        raise ValueError(
            f"'{url}' parece ser um perfil de usuário, não um repositório.\n"
            f"  • Para analisar um repositório específico: https://github.com/{profile.group(1)}/nome-do-repo\n"
            f"  • Para analisar todos os repos do usuário, use a flag --user:\n"
            f"    python main.py --user {profile.group(1)}"
        )
    raise ValueError(
        f"URL inválida: {url}\n"
        f"  Formato esperado: https://github.com/owner/repo"
    )


def parse_user_url(url: str) -> str:
    """Extract username from a GitHub profile URL or plain username."""
    url = url.strip().rstrip("/")
    m = re.search(r"github\.com[/:]([^/\s]+)$", url)
    if m:
        return m.group(1)
    # Accept plain username without URL
    if re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$", url):
        return url
    raise ValueError(f"Não foi possível extrair o usuário GitHub de: {url}")


class GitHubCollector:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        """Make an authenticated GET request to the GitHub API."""
        url = f"{GITHUB_API_BASE}{path}"
        resp = self.session.get(url, params=params, timeout=20)

        remaining = int(resp.headers.get("X-RateLimit-Remaining", 999))
        if remaining < 5:
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(0, reset - time.time()) + 1
            time.sleep(min(wait, 30))

        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            raise RuntimeError(
                "GitHub API rate limit exceeded. Set GITHUB_TOKEN to increase the limit."
            )
        if resp.status_code == 404:
            return None
        if resp.status_code == 401:
            raise RuntimeError("GitHub token is invalid or expired.")
        resp.raise_for_status()
        return resp.json()

    def collect_all(self, github_url: str) -> RepoData:
        owner, repo = parse_github_url(github_url)
        data = RepoData(owner=owner, repo=repo, full_name=f"{owner}/{repo}", description=None, language=None)

        try:
            self._collect_repo_info(data)
            self._collect_languages(data)
            self._collect_commits(data)
            self._collect_branches(data)
            self._collect_prs(data)
            self._collect_issues(data)
            self._collect_file_structure(data)
            self._collect_readme(data)
            self._collect_dependencies(data)
            self._collect_contributors(data)
        except RuntimeError as e:
            data.error = str(e)

        return data

    def _collect_repo_info(self, data: RepoData) -> None:
        info = self._get(f"/repos/{data.owner}/{data.repo}")
        if info is None:
            raise RuntimeError(f"Repository {data.full_name} not found or is private.")
        data.description = info.get("description")
        data.language = info.get("language")
        data.size_kb = info.get("size", 0)
        data.stars = info.get("stargazers_count", 0)
        data.forks = info.get("forks_count", 0)
        data.open_issues = info.get("open_issues_count", 0)
        data.created_at = info.get("created_at")
        data.pushed_at = info.get("pushed_at")
        data.default_branch = info.get("default_branch", "main")
        data.topics = info.get("topics", [])
        data.has_license = info.get("license") is not None

    def _collect_languages(self, data: RepoData) -> None:
        langs = self._get(f"/repos/{data.owner}/{data.repo}/languages")
        if langs:
            data.languages = langs

    def _collect_commits(self, data: RepoData) -> None:
        commits: list[CommitInfo] = []
        page = 1
        while len(commits) < MAX_COMMITS:
            page_data = self._get(
                f"/repos/{data.owner}/{data.repo}/commits",
                params={"per_page": COMMITS_PER_PAGE, "page": page},
            )
            if not page_data:
                break
            for c in page_data:
                commit = c.get("commit", {})
                author_info = commit.get("author") or {}
                committer_info = c.get("author") or {}
                commits.append(
                    CommitInfo(
                        sha=c.get("sha", "")[:7],
                        message=(commit.get("message") or "").split("\n")[0].strip(),
                        date=author_info.get("date"),
                        author=committer_info.get("login", author_info.get("name", "")),
                    )
                )
            if len(page_data) < COMMITS_PER_PAGE:
                break
            page += 1
        data.commits = commits

    def _collect_branches(self, data: RepoData) -> None:
        page_data = self._get(
            f"/repos/{data.owner}/{data.repo}/branches",
            params={"per_page": 100},
        )
        if page_data:
            data.branches = [b["name"] for b in page_data]

    def _collect_prs(self, data: RepoData) -> None:
        prs = self._get(
            f"/repos/{data.owner}/{data.repo}/pulls",
            params={"state": "all", "per_page": 100},
        )
        if prs:
            data.open_prs = sum(1 for p in prs if p.get("state") == "open")
            data.merged_prs = sum(1 for p in prs if p.get("merged_at"))
            data.closed_prs = sum(
                1 for p in prs if p.get("state") == "closed" and not p.get("merged_at")
            )

    def _collect_issues(self, data: RepoData) -> None:
        open_issues = self._get(
            f"/repos/{data.owner}/{data.repo}/issues",
            params={"state": "open", "per_page": 100},
        )
        closed_issues = self._get(
            f"/repos/{data.owner}/{data.repo}/issues",
            params={"state": "closed", "per_page": 100},
        )
        if open_issues:
            data.open_issues_count = len([i for i in open_issues if "pull_request" not in i])
        if closed_issues:
            data.closed_issues_count = len([i for i in closed_issues if "pull_request" not in i])

    def _collect_file_structure(self, data: RepoData) -> None:
        """Recursively explore the repo's file structure up to 2 levels deep."""
        root = self._get(f"/repos/{data.owner}/{data.repo}/contents/")
        if not root or not isinstance(root, list):
            return

        for item in root:
            self._process_root_item(item, data)

        # Check for test files scattered in root
        self._check_scattered_test_files(data)
        # Check for docker-compose
        self._check_docker_presence(data)

    def _process_root_item(self, item: dict, data: RepoData) -> None:
        name = item.get("name", "")
        item_type = item.get("type", "")
        data.all_paths.append(name)

        if item_type == "file":
            data.root_files.append(name)
            self._identify_file_by_name(name, data)
        elif item_type == "dir":
            data.root_dirs.append(name)
            self._scan_directory_logic(name, data)

    def _identify_file_by_name(self, name: str, data: RepoData) -> None:
        lower = name.lower()
        if lower == "dockerfile":
            data.has_dockerfile = True
        if lower == ".gitignore":
            data.has_gitignore = True
        if lower in ["license", "license.md", "license.txt"]:
            data.has_license = True
        
        if self._is_quality_file(name):
            data.quality_files.append(name)
        
        if self._is_ci_file(name):
            data.ci_cd_files.append(name)
            data.has_ci_cd = True

    def _is_quality_file(self, name: str) -> bool:
        quality_patterns = {
            ".editorconfig", ".eslintrc", ".eslintrc.json", ".eslintrc.js",
            ".eslintrc.yml", ".prettierrc", ".prettierrc.json", "pyproject.toml",
            ".flake8", "setup.cfg", ".mypy.ini", "ruff.toml", ".rubocop.yml",
            ".golangci.yml", ".golangci.yaml", "sonar-project.properties",
            "SECURITY.md", "CODE_OF_CONDUCT.md", "CONTRIBUTING.md",
            "CHANGELOG.md", "CHANGELOG",
        }
        return name in quality_patterns or name.lower() in [p.lower() for p in quality_patterns]

    def _is_ci_file(self, name: str) -> bool:
        ci_patterns = {
            ".travis.yml", "Jenkinsfile", ".gitlab-ci.yml", "azure-pipelines.yml", 
            ".drone.yml", "bitbucket-pipelines.yml", "appveyor.yml", "Makefile"
        }
        return name in ci_patterns

    def _scan_directory_logic(self, name: str, data: RepoData) -> None:
        lower = name.lower()
        if lower in ["test", "tests", "__tests__", "spec", "specs", "e2e"]:
            data.has_tests = True
            sub = self._get(f"/repos/{data.owner}/{data.repo}/contents/{name}")
            if sub and isinstance(sub, list):
                data.test_files_count += len([f for f in sub if f.get("type") == "file"])
        
        if name == ".github":
            sub = self._get(f"/repos/{data.owner}/{data.repo}/contents/.github")
            if sub and isinstance(sub, list):
                for sub_item in sub:
                    if sub_item.get("name", "").lower() == "workflows":
                        data.ci_cd_files.append(".github/workflows")
                        data.has_ci_cd = True
        
        if name == ".circleci":
            data.ci_cd_files.append(".circleci/config.yml")
            data.has_ci_cd = True

    def _check_scattered_test_files(self, data: RepoData) -> None:
        test_extensions = {".test.js", ".test.ts", ".spec.js", ".spec.ts", "_test.go", "_test.py"}
        for f in data.root_files:
            if any(f.endswith(ext) for ext in test_extensions):
                data.has_tests = True
                data.test_files_count += 1

    def _check_docker_presence(self, data: RepoData) -> None:
        for f in data.root_files:
            if "docker-compose" in f.lower() or f.lower() == "dockerfile":
                data.has_dockerfile = True

    def _collect_readme(self, data: RepoData) -> None:
        for name in ["README.md", "README.MD", "readme.md", "README", "README.rst"]:
            content_data = self._get(
                f"/repos/{data.owner}/{data.repo}/contents/{name}"
            )
            if content_data and isinstance(content_data, dict):
                import base64
                try:
                    raw = base64.b64decode(content_data.get("content", "")).decode("utf-8", errors="ignore")
                    data.readme_content = raw[:5000]
                    data.readme_length = len(raw)
                except Exception:
                    pass
                break

    def _collect_dependencies(self, data: RepoData) -> None:
        dep_files = [
            "package.json", "requirements.txt", "Pipfile", "pyproject.toml",
            "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
            "Gemfile", "composer.json", "pubspec.yaml",
        ]
        for dep_file in dep_files:
            content_data = self._get(
                f"/repos/{data.owner}/{data.repo}/contents/{dep_file}"
            )
            if content_data and isinstance(content_data, dict):
                import base64
                try:
                    raw = base64.b64decode(content_data.get("content", "")).decode("utf-8", errors="ignore")
                    data.dependency_content[dep_file] = raw[:8000]
                except Exception:
                    pass

    def _collect_contributors(self, data: RepoData) -> None:
        contributors = self._get(
            f"/repos/{data.owner}/{data.repo}/contributors",
            params={"per_page": 100},
        )
        if contributors and isinstance(contributors, list):
            data.contributor_count = len(contributors)

    # ── User profile methods ──────────────────────────────────────────────────

    def get_user_info(self, username: str) -> dict:
        """Fetch basic GitHub user information."""
        info = self._get(f"/users/{username}")
        if info is None:
            raise RuntimeError(f"Usuário '{username}' não encontrado no GitHub.")
        return info

    def get_user_repos(self, username: str, max_repos: int = 10) -> list[dict]:
        """
        Return the user's most relevant repositories.
        Combines owned repos and repos they contributed to via recent events.
        """
        seen: dict[str, dict] = {}

        # 1. Repos owned by the user (sorted by most recently pushed)
        owned = self._get(
            f"/users/{username}/repos",
            params={"type": "owner", "sort": "pushed", "per_page": 30},
        )
        if owned:
            for repo in owned:
                if not repo.get("fork") and not repo.get("archived"):
                    seen[repo["full_name"]] = repo

        # 2. Repos they contributed to via recent push events
        events = self._get(
            f"/users/{username}/events",
            params={"per_page": 100},
        )
        if events:
            contributed_names: list[str] = []
            for event in events:
                if event.get("type") in ("PushEvent", "PullRequestEvent", "CreateEvent"):
                    repo_info = event.get("repo", {})
                    name = repo_info.get("name", "")  # format: owner/repo
                    if name and name not in seen and username.lower() not in name.lower().split("/")[0].lower():
                        contributed_names.append(name)
            # Fetch metadata for unique contributed repos (up to 5)
            for full_name in list(dict.fromkeys(contributed_names))[:5]:
                repo_data = self._get(f"/repos/{full_name}")
                if repo_data and not repo_data.get("archived"):
                    seen[full_name] = repo_data

        # Sort by pushed_at descending and return top N
        repos = sorted(
            seen.values(),
            key=lambda r: r.get("pushed_at") or "",
            reverse=True,
        )
        return repos[:max_repos]
