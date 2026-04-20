"""Basic tests for the GitHub analyzer."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from src.collector import parse_github_url
from src.analyzer import MetricsAnalyzer
from src.collector import RepoData, CommitInfo
from src.config import CONVENTIONAL_COMMIT_RE


# ── URL parsing ──────────────────────────────────────────────────────────────

class TestParseGithubUrl:
    def test_https_url(self):
        owner, repo = parse_github_url("https://github.com/torvalds/linux")
        assert owner == "torvalds"
        assert repo == "linux"

    def test_https_url_with_slash(self):
        owner, repo = parse_github_url("https://github.com/owner/repo/")
        assert owner == "owner"
        assert repo == "repo"

    def test_https_url_with_git(self):
        owner, repo = parse_github_url("https://github.com/owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_http_url(self):
        owner, repo = parse_github_url("http://github.com/owner/myproject")
        assert owner == "owner"
        assert repo == "myproject"

    def test_ssh_style_url(self):
        owner, repo = parse_github_url("git@github.com:owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_enterprise_url(self):
        owner, repo = parse_github_url("https://github.mycompany.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_invalid_url_no_repo(self):
        with pytest.raises(ValueError):
            parse_github_url("not-a-url")


# ── Conventional commit regex ─────────────────────────────────────────────────

class TestConventionalCommitRegex:
    def test_feat(self):
        assert CONVENTIONAL_COMMIT_RE.match("feat: add login endpoint")

    def test_fix_with_scope(self):
        assert CONVENTIONAL_COMMIT_RE.match("fix(auth): handle token expiry")

    def test_chore(self):
        assert CONVENTIONAL_COMMIT_RE.match("chore: update dependencies")

    def test_non_conventional(self):
        assert not CONVENTIONAL_COMMIT_RE.match("update stuff")

    def test_wip_not_conventional(self):
        assert not CONVENTIONAL_COMMIT_RE.match("wip")

    def test_empty(self):
        assert not CONVENTIONAL_COMMIT_RE.match("")


# ── Score computation ─────────────────────────────────────────────────────────

def _make_repo_data(**kwargs) -> RepoData:
    defaults = dict(
        owner="test", repo="repo", full_name="test/repo",
        description="Test repo", language="Python",
        languages={"Python": 10000},
        commits=[],
        root_files=[], root_dirs=[], all_paths=[],
        quality_files=[],
        readme_length=500,
        dependency_content={},
        ci_cd_files=[],
        branches=["main"],
    )
    defaults.update(kwargs)
    return RepoData(**defaults)


class TestSeniority:
    def test_empty_repo_is_junior(self):
        data = _make_repo_data()
        result = MetricsAnalyzer().analyze(data)
        assert result.seniority == "junior"

    def test_high_quality_repo_is_senior(self):
        commits = [
            CommitInfo(sha="abc", message="feat: add user auth", date="2024-01-01T00:00:00Z")
            for _ in range(50)
        ] + [
            CommitInfo(sha="def", message="fix(db): correct migration", date="2024-06-01T00:00:00Z")
            for _ in range(50)
        ]
        data = _make_repo_data(
            commits=commits,
            has_tests=True,
            test_files_count=15,
            has_ci_cd=True,
            ci_cd_files=[".github/workflows"],
            has_dockerfile=True,
            readme_length=3000,
            root_dirs=["src", "tests", "docs", "scripts", "config"],
            quality_files=["CONTRIBUTING.md", ".eslintrc.json"],
            has_gitignore=True,
            has_license=True,
            branches=["main", "dev", "feature/auth"],
            open_prs=2,
            merged_prs=15,
            closed_prs=3,
            open_issues_count=3,
            closed_issues_count=20,
            dependency_content={"package.json": '{"dependencies": {"react": "18.0.0", "eslint": "8.0.0"}}'},
        )
        result = MetricsAnalyzer().analyze(data)
        assert result.seniority in ("mid-level", "senior")
        assert result.composite_score >= 35

    def test_composite_score_range(self):
        data = _make_repo_data()
        result = MetricsAnalyzer().analyze(data)
        assert 0 <= result.composite_score <= 100


# ── Framework detection ────────────────────────────────────────────────────────

class TestFrameworkDetection:
    def test_detects_react(self):
        data = _make_repo_data(
            dependency_content={"package.json": '{"dependencies": {"react": "18.0.0"}}'}
        )
        result = MetricsAnalyzer().analyze(data)
        assert "React" in result.frameworks

    def test_detects_django(self):
        data = _make_repo_data(
            dependency_content={"requirements.txt": "django==4.2\ngunicorn==21.0"}
        )
        result = MetricsAnalyzer().analyze(data)
        assert "Django" in result.frameworks

    def test_no_frameworks_when_empty(self):
        data = _make_repo_data()
        result = MetricsAnalyzer().analyze(data)
        assert result.frameworks == []


# ── Developer profile detection ───────────────────────────────────────────────

class TestProfileDetection:
    def test_detects_frontend(self):
        data = _make_repo_data(
            languages={"TypeScript": 8000, "CSS": 2000},
            dependency_content={"package.json": '{"dependencies": {"react": "18.0.0", "vite": "5.0.0"}}'},
        )
        result = MetricsAnalyzer().analyze(data)
        assert "Frontend" in result.detected_profile or "Fullstack" in result.detected_profile

    def test_detects_backend_python(self):
        data = _make_repo_data(
            languages={"Python": 15000},
            dependency_content={"requirements.txt": "fastapi==0.100\nuvicorn==0.23\nsqlalchemy==2.0"},
        )
        result = MetricsAnalyzer().analyze(data)
        assert "Backend" in result.detected_profile or "Data" in result.detected_profile

    def test_detects_ml(self):
        data = _make_repo_data(
            languages={"Python": 15000, "Jupyter Notebook": 5000},
            dependency_content={"requirements.txt": "numpy\npandas\nscikit-learn\ntensorflow"},
        )
        result = MetricsAnalyzer().analyze(data)
        assert "Data" in result.detected_profile


# ── Commit quality scoring ────────────────────────────────────────────────────

class TestCommitQuality:
    def test_conventional_commits_improve_score(self):
        good_commits = [
            CommitInfo(sha=f"{i}", message=f"feat(module{i}): implement feature {i}", date="2024-01-01T00:00:00Z")
            for i in range(30)
        ]
        data_good = _make_repo_data(commits=good_commits)

        bad_commits = [
            CommitInfo(sha=f"{i}", message="wip", date="2024-01-01T00:00:00Z")
            for i in range(30)
        ]
        data_bad = _make_repo_data(commits=bad_commits)

        result_good = MetricsAnalyzer().analyze(data_good)
        result_bad = MetricsAnalyzer().analyze(data_bad)

        good_cq = next(d.score for d in result_good.dimensions if "Commit" in d.name)
        bad_cq = next(d.score for d in result_bad.dimensions if "Commit" in d.name)

        assert good_cq > bad_cq

    def test_conventional_ratio_correct(self):
        commits = [
            CommitInfo(sha="1", message="feat: add something", date="2024-01-01T00:00:00Z"),
            CommitInfo(sha="2", message="fix: correct bug", date="2024-01-01T00:00:00Z"),
            CommitInfo(sha="3", message="random message", date="2024-01-01T00:00:00Z"),
            CommitInfo(sha="4", message="another random", date="2024-01-01T00:00:00Z"),
        ]
        data = _make_repo_data(commits=commits)
        result = MetricsAnalyzer().analyze(data)
        assert abs(result.conventional_commit_ratio - 0.5) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
