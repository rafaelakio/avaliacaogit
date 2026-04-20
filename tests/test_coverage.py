"""Extended test suite targeting ≥80% coverage across all src modules."""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.analyzer import MetricsAnalyzer, AnalysisResult, ScoreDimension, aggregate_results
from src.ai_analyzer import AIAnalyzer, TextualAnalysis
from src.collector import (
    GitHubCollector, RepoData, CommitInfo,
    parse_github_url, parse_user_url,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _repo(**kwargs) -> RepoData:
    defaults = dict(
        owner="user", repo="proj", full_name="user/proj",
        description="desc", language="Python",
        languages={"Python": 5000},
        commits=[], root_files=[], root_dirs=[], all_paths=[],
        quality_files=[], readme_length=0,
        dependency_content={}, ci_cd_files=[], branches=["main"],
    )
    defaults.update(kwargs)
    return RepoData(**defaults)


def _result(**kwargs) -> AnalysisResult:
    r = AnalysisResult(repo="proj", owner="user", description="d")
    for k, v in kwargs.items():
        setattr(r, k, v)
    return r


# ─── analyzer._score_commit_quality ───────────────────────────────────────────

class TestScoreCommitQuality:
    def test_no_commits_returns_zero(self):
        r = _result(total_commits_sampled=0)
        dim = MetricsAnalyzer()._score_commit_quality(r)
        assert dim.score == 0.0

    def test_short_messages_low_score(self):
        r = _result(
            total_commits_sampled=5,
            conventional_commit_ratio=0.0,
            avg_message_length=10,
            wip_commit_ratio=0.5,
        )
        dim = MetricsAnalyzer()._score_commit_quality(r)
        assert dim.score < 20

    def test_medium_messages(self):
        r = _result(
            total_commits_sampled=5,
            conventional_commit_ratio=0.0,
            avg_message_length=30,
            wip_commit_ratio=0.0,
        )
        dim = MetricsAnalyzer()._score_commit_quality(r)
        assert dim.score >= 15

    def test_long_messages_high_conv_low_wip(self):
        r = _result(
            total_commits_sampled=25,
            conventional_commit_ratio=1.0,
            avg_message_length=60,
            wip_commit_ratio=0.0,
        )
        dim = MetricsAnalyzer()._score_commit_quality(r)
        assert dim.score == 100.0

    def test_wip_between_10_and_30_percent(self):
        r = _result(
            total_commits_sampled=5,
            conventional_commit_ratio=0.0,
            avg_message_length=30,
            wip_commit_ratio=0.2,
        )
        dim = MetricsAnalyzer()._score_commit_quality(r)
        assert dim.score >= 10


# ─── analyzer._score_testing ──────────────────────────────────────────────────

class TestScoreTesting:
    def test_no_tests_zero(self):
        r = _result(has_tests=False, test_files_count=0, frameworks=[])
        dim = MetricsAnalyzer()._score_testing(r)
        assert dim.score == 0.0

    def test_has_tests_single_file(self):
        r = _result(has_tests=True, test_files_count=1, frameworks=[])
        dim = MetricsAnalyzer()._score_testing(r)
        assert dim.score == 60  # 50 + 10

    def test_has_tests_3_plus_files(self):
        r = _result(has_tests=True, test_files_count=5, frameworks=[])
        dim = MetricsAnalyzer()._score_testing(r)
        assert dim.score == 70  # 50 + 20

    def test_has_tests_10_plus_files(self):
        r = _result(has_tests=True, test_files_count=12, frameworks=[])
        dim = MetricsAnalyzer()._score_testing(r)
        assert dim.score == 80  # 50 + 30

    def test_test_framework_bonus(self):
        r = _result(has_tests=True, test_files_count=5, frameworks=["pytest"])
        dim = MetricsAnalyzer()._score_testing(r)
        assert dim.score == 90  # 50 + 20 + 20


# ─── analyzer._score_cicd ─────────────────────────────────────────────────────

class TestScoreCicd:
    def test_nothing(self):
        r = _result(has_ci_cd=False, has_dockerfile=False, ci_cd_systems=[])
        dim = MetricsAnalyzer()._score_cicd(r)
        assert dim.score == 0

    def test_only_ci(self):
        r = _result(has_ci_cd=True, has_dockerfile=False, ci_cd_systems=["github_actions"])
        dim = MetricsAnalyzer()._score_cicd(r)
        assert dim.score == 60

    def test_ci_and_docker(self):
        r = _result(has_ci_cd=True, has_dockerfile=True, ci_cd_systems=["github_actions"])
        dim = MetricsAnalyzer()._score_cicd(r)
        assert dim.score == 85

    def test_ci_docker_two_systems(self):
        r = _result(has_ci_cd=True, has_dockerfile=True, ci_cd_systems=["github_actions", ".travis.yml"])
        dim = MetricsAnalyzer()._score_cicd(r)
        assert dim.score == 100


# ─── analyzer._score_documentation ───────────────────────────────────────────

class TestScoreDocumentation:
    def setup_method(self):
        self.az = MetricsAnalyzer()

    def _data(self, **kw):
        return _repo(**kw)

    def test_no_readme(self):
        r = _result(readme_quality="none", has_contributing=False, has_changelog=False)
        dim = self.az._score_documentation(self._data(has_license=False), r)
        assert dim.score == 0

    def test_minimal_readme(self):
        r = _result(readme_quality="minimal", has_contributing=False, has_changelog=False)
        dim = self.az._score_documentation(self._data(has_license=False), r)
        assert dim.score == 10

    def test_basic_readme(self):
        r = _result(readme_quality="basic", has_contributing=False, has_changelog=False)
        dim = self.az._score_documentation(self._data(has_license=False), r)
        assert dim.score == 30

    def test_good_readme(self):
        r = _result(readme_quality="good", has_contributing=False, has_changelog=False)
        dim = self.az._score_documentation(self._data(has_license=False), r)
        assert dim.score == 55

    def test_comprehensive_with_all(self):
        r = _result(readme_quality="comprehensive", has_contributing=True, has_changelog=True)
        dim = self.az._score_documentation(self._data(has_license=True), r)
        assert dim.score == 100  # 70+15+10+5

    def test_contributing_bonus(self):
        r = _result(readme_quality="none", has_contributing=True, has_changelog=False)
        dim = self.az._score_documentation(self._data(has_license=False), r)
        assert dim.score == 15


# ─── analyzer._score_project_structure ───────────────────────────────────────

class TestScoreProjectStructure:
    def setup_method(self):
        self.az = MetricsAnalyzer()

    def test_flat_no_gitignore(self):
        r = _result(project_structure="flat")
        dim = self.az._score_project_structure(_repo(has_gitignore=False), r)
        assert dim.score == 10

    def test_flat_with_gitignore(self):
        r = _result(project_structure="flat")
        dim = self.az._score_project_structure(_repo(has_gitignore=True), r)
        assert dim.score == 20

    def test_organized(self):
        r = _result(project_structure="organized")
        dim = self.az._score_project_structure(_repo(has_gitignore=False), r)
        assert dim.score == 65

    def test_well_organized_with_gitignore(self):
        r = _result(project_structure="well-organized")
        dim = self.az._score_project_structure(_repo(has_gitignore=True), r)
        assert dim.score == 100


# ─── analyzer._score_frameworks ───────────────────────────────────────────────

class TestScoreFrameworks:
    def setup_method(self):
        self.az = MetricsAnalyzer()

    def test_no_frameworks_no_deps(self):
        r = _result(frameworks=[])
        dim = self.az._score_frameworks(_repo(dependency_content={}, topics=[]), r)
        assert dim.score == 0

    def test_has_deps_bonus(self):
        r = _result(frameworks=[])
        dim = self.az._score_frameworks(_repo(dependency_content={"req.txt": "x"}, topics=[]), r)
        assert dim.score == 15

    def test_linting_bonus(self):
        r = _result(frameworks=["ESLint", "Prettier"])
        dim = self.az._score_frameworks(_repo(dependency_content={"p.json": "{}"}, topics=["js"]), r)
        assert dim.score >= 40

    def test_many_frameworks_capped(self):
        r = _result(frameworks=["A", "B", "C", "D", "E", "F", "G", "H", "I"])
        dim = self.az._score_frameworks(_repo(dependency_content={}, topics=[]), r)
        assert dim.score <= 100


# ─── analyzer._score_pr_workflow ──────────────────────────────────────────────

class TestScorePrWorkflow:
    def setup_method(self):
        self.az = MetricsAnalyzer()

    def test_no_prs(self):
        r = _result(branch_count=1)
        dim = self.az._score_pr_workflow(_repo(open_prs=0, merged_prs=0, closed_prs=0), r)
        assert dim.score == 0

    def test_one_pr(self):
        r = _result(branch_count=1)
        # 1 merged PR: 20 (base) + 0 (branches) + 15 (merged ratio > 0.5) = 35
        dim = self.az._score_pr_workflow(_repo(open_prs=0, merged_prs=1, closed_prs=0), r)
        assert dim.score == 35

    def test_five_plus_prs_two_branches(self):
        r = _result(branch_count=2)
        dim = self.az._score_pr_workflow(_repo(open_prs=2, merged_prs=4, closed_prs=0), r)
        assert dim.score >= 40

    def test_merged_ratio_bonus(self):
        r = _result(branch_count=3)
        dim = self.az._score_pr_workflow(_repo(open_prs=0, merged_prs=15, closed_prs=5), r)
        assert dim.score >= 75


# ─── analyzer._score_issue_tracking ───────────────────────────────────────────

class TestScoreIssueTracking:
    def setup_method(self):
        self.az = MetricsAnalyzer()

    def test_no_issues(self):
        dim = self.az._score_issue_tracking(_repo(open_issues_count=0, closed_issues_count=0), _result())
        assert dim.score == 0

    def test_some_issues_mostly_closed(self):
        dim = self.az._score_issue_tracking(_repo(open_issues_count=2, closed_issues_count=10), _result())
        assert dim.score >= 60

    def test_twenty_plus_issues_half_closed(self):
        dim = self.az._score_issue_tracking(_repo(open_issues_count=10, closed_issues_count=15), _result())
        assert dim.score == 100


# ─── analyzer._evaluate_complexity ────────────────────────────────────────────

class TestEvaluateComplexity:
    def setup_method(self):
        self.az = MetricsAnalyzer()

    def test_low_complexity(self):
        r = _result()
        r.dimensions = [ScoreDimension("X", 20.0), ScoreDimension("Y", 25.0)]
        self.az._evaluate_complexity(r)
        assert r.complexity_level == "low"

    def test_medium_complexity(self):
        r = _result()
        r.dimensions = [ScoreDimension("X", 40.0), ScoreDimension("Y", 45.0)]
        self.az._evaluate_complexity(r)
        assert r.complexity_level == "medium"

    def test_high_complexity(self):
        r = _result()
        r.dimensions = [ScoreDimension("X", 70.0), ScoreDimension("Y", 75.0)]
        self.az._evaluate_complexity(r)
        assert r.complexity_level == "high"


# ─── analyzer._detect_profile ─────────────────────────────────────────────────

class TestDetectProfile:
    def setup_method(self):
        self.az = MetricsAnalyzer()

    def test_devops_profile(self):
        data = _repo(
            has_dockerfile=True,
            ci_cd_files=[".github/workflows"],
            topics=["kubernetes", "terraform"],
            languages={"HCL": 1000},
        )
        result = _result(languages=["hcl"], frameworks=["Kubernetes", "Terraform"])
        self.az._detect_profile(data, result)
        assert "DevOps" in result.detected_profile

    def test_mobile_profile_swift(self):
        data = _repo(languages={"Swift": 5000})
        result = _result(languages=["swift"], frameworks=[])
        self.az._detect_profile(data, result)
        assert "Mobile" in result.detected_profile

    def test_mobile_profile_flutter(self):
        data = _repo(languages={"Dart": 5000})
        result = _result(languages=["dart"], frameworks=["Flutter"])
        self.az._detect_profile(data, result)
        assert "Mobile" in result.detected_profile

    def test_fullstack_profile(self):
        data = _repo(
            dependency_content={"package.json": '{"dependencies":{"react":"18","express":"4"}}'}
        )
        result = _result(languages=["typescript", "javascript"], frameworks=["React", "Express"])
        self.az._detect_profile(data, result)
        assert "Fullstack" in result.detected_profile or "Frontend" in result.detected_profile

    def test_unknown_language_fallback(self):
        data = _repo(languages={"Cobol": 100})
        result = _result(languages=["cobol"], primary_language="Cobol", frameworks=[])
        self.az._detect_profile(data, result)
        assert result.detected_profile != ""

    def test_no_languages_fallback(self):
        data = _repo(languages={})
        result = _result(languages=[], primary_language=None, frameworks=[])
        self.az._detect_profile(data, result)
        assert result.detected_profile == "Software Developer"


# ─── analyzer._analyze_structure ──────────────────────────────────────────────

class TestAnalyzeStructure:
    def setup_method(self):
        self.az = MetricsAnalyzer()

    def test_readme_none(self):
        data = _repo(readme_length=0)
        r = _result()
        self.az._analyze_structure(data, r)
        assert r.readme_quality == "none"

    def test_readme_minimal(self):
        data = _repo(readme_length=200)
        r = _result()
        self.az._analyze_structure(data, r)
        assert r.readme_quality == "minimal"

    def test_readme_basic(self):
        data = _repo(readme_length=800)
        r = _result()
        self.az._analyze_structure(data, r)
        assert r.readme_quality == "basic"

    def test_readme_good(self):
        data = _repo(readme_length=2000)
        r = _result()
        self.az._analyze_structure(data, r)
        assert r.readme_quality == "good"

    def test_readme_comprehensive(self):
        data = _repo(readme_length=6000)
        r = _result()
        self.az._analyze_structure(data, r)
        assert r.readme_quality == "comprehensive"

    def test_structure_basic(self):
        data = _repo(root_dirs=["src"])
        r = _result()
        self.az._analyze_structure(data, r)
        assert r.project_structure == "basic"

    def test_structure_organized(self):
        data = _repo(root_dirs=["src", "tests", "docs"])
        r = _result()
        self.az._analyze_structure(data, r)
        assert r.project_structure == "organized"

    def test_structure_well_organized(self):
        data = _repo(root_dirs=["src", "tests", "docs", "scripts", "infra"])
        r = _result()
        self.az._analyze_structure(data, r)
        assert r.project_structure == "well-organized"

    def test_contributing_and_changelog_detected(self):
        data = _repo(root_files=["CONTRIBUTING.md", "CHANGELOG.md"])
        r = _result()
        self.az._analyze_structure(data, r)
        assert r.has_contributing is True
        assert r.has_changelog is True

    def test_ignored_dirs_not_counted(self):
        data = _repo(root_dirs=["node_modules", ".git", ".venv"])
        r = _result()
        self.az._analyze_structure(data, r)
        assert r.project_structure == "flat"

    def test_solo_project_false(self):
        data = _repo(contributor_count=5)
        r = _result()
        self.az._analyze_structure(data, r)
        assert r.is_solo_project is False


# ─── aggregate_results ────────────────────────────────────────────────────────

class TestAggregateResults:
    def _make_result(self, commits=10, seniority="junior", score=30.0):
        data = _repo(
            commits=[CommitInfo(sha=str(i), message=f"feat: x{i}", date="2024-01-01T00:00:00Z") for i in range(commits)],
            has_tests=True, test_files_count=3, has_ci_cd=True,
            ci_cd_files=["gh"], has_dockerfile=False, readme_length=1000,
            root_dirs=["src", "tests", "docs"],
            quality_files=["CONTRIBUTING.md"],
            branches=["main", "dev"],
        )
        result = MetricsAnalyzer().analyze(data)
        return result

    def test_aggregate_single_result(self):
        r = self._make_result()
        agg = aggregate_results([r], "user", {"bio": "dev", "followers": 10, "public_repos": 5})
        assert agg.owner == "user"
        assert agg.total_commits_sampled == r.total_commits_sampled

    def test_aggregate_multiple_results(self):
        r1 = self._make_result(commits=10)
        r2 = self._make_result(commits=20)
        agg = aggregate_results([r1, r2], "user", {"bio": "dev"})
        assert agg.total_commits_sampled == r1.total_commits_sampled + r2.total_commits_sampled

    def test_aggregate_raises_on_empty(self):
        with pytest.raises(ValueError, match="No results"):
            aggregate_results([], "user", {})

    def test_aggregate_best_readme_wins(self):
        r1 = self._make_result()
        r2 = self._make_result()
        r1.readme_quality = "minimal"
        r2.readme_quality = "comprehensive"
        agg = aggregate_results([r1, r2], "user", {})
        assert agg.readme_quality == "comprehensive"

    def test_aggregate_best_structure_wins(self):
        r1 = self._make_result()
        r2 = self._make_result()
        r1.project_structure = "flat"
        r2.project_structure = "well-organized"
        agg = aggregate_results([r1, r2], "user", {})
        assert agg.project_structure == "well-organized"

    def test_aggregate_has_tests_any(self):
        r1 = self._make_result()
        r2 = self._make_result()
        r1.has_tests = False
        r2.has_tests = True
        agg = aggregate_results([r1, r2], "user", {})
        assert agg.has_tests is True

    def test_aggregate_repo_names_in_raw_summary(self):
        r = self._make_result()
        agg = aggregate_results([r], "testuser", {"bio": ""})
        assert "repo_names" in agg.raw_summary
        assert len(agg.raw_summary["repo_names"]) == 1


# ─── AIAnalyzer._fallback_analysis ────────────────────────────────────────────

class TestAIAnalyzerFallback:
    def setup_method(self):
        self.ai = AIAnalyzer(api_key="")  # no key → always fallback

    def _full_result(self, **kwargs) -> AnalysisResult:
        data = _repo(
            has_tests=True, test_files_count=5,
            has_ci_cd=True, ci_cd_files=["github_actions"],
            readme_length=2000, root_dirs=["src", "tests"],
            quality_files=["CONTRIBUTING.md"],
            commits=[
                CommitInfo(sha="1", message="feat: x", date="2024-01-01T00:00:00Z"),
                CommitInfo(sha="2", message="fix: y", date="2024-06-01T00:00:00Z"),
            ],
            branches=["main", "dev"],
            **kwargs
        )
        r = MetricsAnalyzer().analyze(data)
        return r

    def test_client_is_none_when_no_key(self):
        assert self.ai.client is None

    def test_fallback_returns_textual_analysis(self):
        result = self._full_result()
        ta = self.ai.analyze(result)
        assert isinstance(ta, TextualAnalysis)
        assert ta.used_ai is False

    def test_fallback_with_good_practices(self):
        result = self._full_result()
        result.conventional_commit_ratio = 0.9
        result.has_tests = True
        result.has_ci_cd = True
        result.readme_quality = "good"
        ta = self.ai._fallback_analysis(result)
        assert len(ta.strengths) > 0

    def test_fallback_recommendations_no_tests(self):
        result = self._full_result()
        result.has_tests = False
        result.has_ci_cd = False
        result.conventional_commit_ratio = 0.0
        result.readme_quality = "none"
        result.has_contributing = False
        ta = self.ai._fallback_analysis(result)
        recs_text = " ".join(ta.recommendations)
        assert "test" in recs_text.lower() or "ci" in recs_text.lower() or "readme" in recs_text.lower()

    def test_fallback_no_recommendations_high_quality(self):
        result = self._full_result()
        result.has_tests = True
        result.has_ci_cd = True
        result.conventional_commit_ratio = 0.9
        result.readme_quality = "good"
        result.has_contributing = True
        ta = self.ai._fallback_analysis(result)
        assert len(ta.recommendations) > 0  # at least "continue maintaining"

    def test_fallback_solo_project_mention(self):
        result = self._full_result()
        result.is_solo_project = True
        ta = self.ai._fallback_analysis(result)
        assert "solo" in ta.developer_profile.lower()

    def test_fallback_full_text_contains_rule_based(self):
        result = self._full_result()
        ta = self.ai._fallback_analysis(result)
        assert "Rule-based" in ta.full_text or "rule-based" in ta.full_text.lower()


# ─── AIAnalyzer._parse_ai_response ────────────────────────────────────────────

class TestAIAnalyzerParseResponse:
    def setup_method(self):
        self.ai = AIAnalyzer(api_key="")

    def _valid_json(self):
        return json.dumps({
            "developer_profile": "Backend developer",
            "seniority_estimate": "senior",
            "seniority_justification": "Strong practices.",
            "strengths": ["Testing", "CI/CD"],
            "weaknesses": ["Documentation"],
            "recommendations": ["Add more docs"],
        })

    def test_parse_valid_json(self):
        ta = self.ai._parse_ai_response(self._valid_json())
        assert ta.developer_profile == "Backend developer"
        assert ta.seniority_estimate == "senior"
        assert ta.used_ai is True

    def test_parse_json_with_markdown_fences(self):
        raw = "```json\n" + self._valid_json() + "\n```"
        ta = self.ai._parse_ai_response(raw)
        assert ta.developer_profile == "Backend developer"

    def test_parse_json_with_plain_fences(self):
        raw = "```\n" + self._valid_json() + "\n```"
        ta = self.ai._parse_ai_response(raw)
        assert ta.seniority_estimate == "senior"

    def test_parse_invalid_json_returns_full_text(self):
        ta = self.ai._parse_ai_response("not json at all !!!")
        assert ta.full_text == "not json at all !!!"
        assert ta.developer_profile == ""

    def test_parse_json_embedded_in_text(self):
        raw = "Here is the result: " + self._valid_json() + " end."
        ta = self.ai._parse_ai_response(raw)
        assert ta.developer_profile == "Backend developer"

    def test_parse_empty_lists_gracefully(self):
        raw = json.dumps({
            "developer_profile": "dev",
            "seniority_estimate": "junior",
            "seniority_justification": "low score",
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        })
        ta = self.ai._parse_ai_response(raw)
        assert ta.strengths == []
        assert ta.weaknesses == []


# ─── collector._scan_directory_logic ──────────────────────────────────────────

class TestScanDirectoryLogic:
    def setup_method(self):
        self.collector = GitHubCollector(token="fake")

    def test_test_dir_sets_has_tests(self):
        data = _repo()
        with patch.object(self.collector, "_get", return_value=[
            {"type": "file", "name": "test_app.py"},
            {"type": "file", "name": "test_utils.py"},
        ]):
            self.collector._scan_directory_logic("tests", data)
        assert data.has_tests is True
        assert data.test_files_count == 2

    def test_spec_dir_sets_has_tests(self):
        data = _repo()
        with patch.object(self.collector, "_get", return_value=[
            {"type": "file", "name": "app.spec.js"},
        ]):
            self.collector._scan_directory_logic("spec", data)
        assert data.has_tests is True

    def test_github_dir_sets_ci_cd(self):
        data = _repo()
        with patch.object(self.collector, "_get", return_value=[
            {"name": "workflows", "type": "dir"},
        ]):
            self.collector._scan_directory_logic(".github", data)
        assert data.has_ci_cd is True
        assert ".github/workflows" in data.ci_cd_files

    def test_circleci_dir_sets_ci_cd(self):
        data = _repo()
        self.collector._scan_directory_logic(".circleci", data)
        assert data.has_ci_cd is True
        assert ".circleci/config.yml" in data.ci_cd_files


# ─── collector._check_scattered_test_files ────────────────────────────────────

class TestCheckScatteredTestFiles:
    def setup_method(self):
        self.collector = GitHubCollector(token="fake")

    def test_detects_jest_test_file(self):
        data = _repo(root_files=["app.test.js"])
        self.collector._check_scattered_test_files(data)
        assert data.has_tests is True
        assert data.test_files_count == 1

    def test_detects_spec_ts_file(self):
        data = _repo(root_files=["component.spec.ts"])
        self.collector._check_scattered_test_files(data)
        assert data.has_tests is True

    def test_detects_go_test_file(self):
        data = _repo(root_files=["main_test.go"])
        self.collector._check_scattered_test_files(data)
        assert data.has_tests is True

    def test_no_test_files(self):
        data = _repo(root_files=["main.py", "utils.py"])
        self.collector._check_scattered_test_files(data)
        assert data.has_tests is False

    def test_multiple_test_files_counted(self):
        data = _repo(root_files=["a.test.js", "b.test.ts", "c.spec.js"])
        self.collector._check_scattered_test_files(data)
        assert data.test_files_count == 3


# ─── collector._check_docker_presence ─────────────────────────────────────────

class TestCheckDockerPresence:
    def setup_method(self):
        self.collector = GitHubCollector(token="fake")

    def test_dockerfile_sets_flag(self):
        data = _repo(root_files=["Dockerfile"])
        self.collector._check_docker_presence(data)
        assert data.has_dockerfile is True

    def test_docker_compose_sets_flag(self):
        data = _repo(root_files=["docker-compose.yml"])
        self.collector._check_docker_presence(data)
        assert data.has_dockerfile is True

    def test_no_docker_files(self):
        data = _repo(root_files=["main.py"])
        self.collector._check_docker_presence(data)
        assert data.has_dockerfile is False


# ─── collector parse functions (extra edge cases) ─────────────────────────────

class TestParseGithubUrlExtra:
    def test_url_with_trailing_slash(self):
        owner, repo = parse_github_url("https://github.com/owner/repo/")
        assert owner == "owner" and repo == "repo"

    def test_ssh_style(self):
        owner, repo = parse_github_url("git@github.com:owner/repo.git")
        assert owner == "owner" and repo == "repo"

    def test_user_profile_error_message(self):
        with pytest.raises(ValueError, match="perfil de usuário"):
            parse_github_url("https://github.com/octocat")

    def test_non_github_domain(self):
        with pytest.raises(ValueError):
            parse_github_url("https://gitlab.com/owner/repo")


class TestParseUserUrlExtra:
    def test_plain_username(self):
        assert parse_user_url("torvalds") == "torvalds"

    def test_url_with_username(self):
        assert parse_user_url("https://github.com/torvalds") == "torvalds"

    def test_url_with_trailing_slash(self):
        assert parse_user_url("https://github.com/torvalds/") == "torvalds"

    def test_invalid_username_with_spaces(self):
        with pytest.raises(ValueError):
            parse_user_url("invalid user")

    def test_invalid_username_special_chars(self):
        with pytest.raises(ValueError):
            parse_user_url("user@name!")


# ─── collector._identify_file_by_name (extra) ─────────────────────────────────

class TestIdentifyFileByName:
    def setup_method(self):
        self.collector = GitHubCollector(token="fake")

    def test_quality_file_contributing(self):
        data = _repo()
        self.collector._identify_file_by_name("CONTRIBUTING.md", data)
        assert "CONTRIBUTING.md" in data.quality_files

    def test_license_txt(self):
        data = _repo()
        self.collector._identify_file_by_name("license.txt", data)
        assert data.has_license is True

    def test_ci_file_travis(self):
        data = _repo()
        self.collector._identify_file_by_name(".travis.yml", data)
        assert data.has_ci_cd is True

    def test_regular_file_no_effect(self):
        data = _repo()
        self.collector._identify_file_by_name("main.py", data)
        assert data.has_dockerfile is False
        assert data.has_gitignore is False


# ─── collector._get (session mock) ────────────────────────────────────────────

class TestCollectorGet:
    def _mock_response(self, status=200, json_data=None, headers=None, text=""):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = json_data or {}
        resp.headers = {"X-RateLimit-Remaining": "50", **(headers or {})}
        resp.text = text
        resp.raise_for_status = MagicMock()
        return resp

    def test_returns_json_on_200(self):
        collector = GitHubCollector(token="tok")
        collector.session.get = MagicMock(return_value=self._mock_response(json_data={"id": 1}))
        result = collector._get("/repos/owner/repo")
        assert result == {"id": 1}

    def test_returns_none_on_404(self):
        collector = GitHubCollector(token="tok")
        collector.session.get = MagicMock(return_value=self._mock_response(status=404))
        result = collector._get("/repos/owner/repo")
        assert result is None

    def test_raises_on_401(self):
        collector = GitHubCollector(token="tok")
        collector.session.get = MagicMock(return_value=self._mock_response(status=401))
        with pytest.raises(RuntimeError, match="invalid or expired"):
            collector._get("/repos/owner/repo")

    def test_raises_on_rate_limit(self):
        collector = GitHubCollector(token="tok")
        collector.session.get = MagicMock(return_value=self._mock_response(
            status=403, text="rate limit exceeded"
        ))
        with pytest.raises(RuntimeError, match="rate limit"):
            collector._get("/repos/owner/repo")

    def test_sleeps_when_remaining_low(self):
        import time as _time
        collector = GitHubCollector(token="tok")
        resp = self._mock_response(
            json_data={"id": 1},
            headers={"X-RateLimit-Remaining": "2", "X-RateLimit-Reset": str(int(_time.time()) + 1)},
        )
        collector.session.get = MagicMock(return_value=resp)
        with patch("src.collector.time.sleep") as mock_sleep:
            collector._get("/repos/owner/repo")
        mock_sleep.assert_called_once()


# ─── collector.collect_all (end-to-end with mock) ─────────────────────────────

import base64


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def _make_collector_mock():
    """Return a GitHubCollector with _get mocked for a standard 'owner/repo'."""
    collector = GitHubCollector(token="fake")

    repo_info = {
        "description": "A test repo", "language": "Python",
        "size": 500, "stargazers_count": 10, "forks_count": 2,
        "open_issues_count": 3, "created_at": "2023-01-01T00:00:00Z",
        "pushed_at": "2024-01-01T00:00:00Z", "default_branch": "main",
        "topics": ["python", "api"], "license": {"spdx_id": "MIT"},
    }
    commits_page = [
        {
            "sha": f"abc{i}",
            "commit": {
                "message": f"feat: feature {i}",
                "author": {"date": f"2024-0{(i % 9) + 1}-01T00:00:00Z", "name": "dev"},
            },
            "author": {"login": "dev"},
        }
        for i in range(5)
    ]
    root_contents = [
        {"name": "README.md", "type": "file"},
        {"name": "requirements.txt", "type": "file"},
        {"name": "Dockerfile", "type": "file"},
        {"name": ".gitignore", "type": "file"},
        {"name": "src", "type": "dir"},
        {"name": "tests", "type": "dir"},
        {"name": ".github", "type": "dir"},
        {"name": "CONTRIBUTING.md", "type": "file"},
    ]
    github_sub = [{"name": "workflows", "type": "dir"}]
    tests_sub = [{"type": "file", "name": "test_app.py"}, {"type": "file", "name": "test_utils.py"}]

    def _get(path, params=None):
        if path == "/repos/owner/repo":
            return repo_info
        if path == "/repos/owner/repo/languages":
            return {"Python": 8000, "Shell": 200}
        if path == "/repos/owner/repo/commits":
            page = (params or {}).get("page", 1)
            return commits_page if page == 1 else []
        if path == "/repos/owner/repo/branches":
            return [{"name": "main"}, {"name": "dev"}]
        if path == "/repos/owner/repo/pulls":
            return [{"state": "closed", "merged_at": "2024-01-01T00:00:00Z"}]
        if path == "/repos/owner/repo/issues":
            state = (params or {}).get("state", "open")
            return [{"title": "issue", "state": state}]
        if path == "/repos/owner/repo/contents/":
            return root_contents
        if path == "/repos/owner/repo/contents/tests":
            return tests_sub
        if path == "/repos/owner/repo/contents/.github":
            return github_sub
        if path == "/repos/owner/repo/contents/README.md":
            return {"content": _b64("# Title\n" + "text " * 300)}
        if path == "/repos/owner/repo/contents/requirements.txt":
            return {"content": _b64("django==4.2\nfastapi==0.100\npytest==7.0")}
        if path == "/repos/owner/repo/contributors":
            return [{"login": "dev"}, {"login": "other"}]
        return None

    collector._get = _get
    return collector


class TestCollectAll:
    def test_collect_all_basic(self):
        collector = _make_collector_mock()
        data = collector.collect_all("https://github.com/owner/repo")
        assert data.owner == "owner"
        assert data.repo == "repo"
        assert data.description == "A test repo"
        assert data.error is None

    def test_collect_languages(self):
        collector = _make_collector_mock()
        data = collector.collect_all("https://github.com/owner/repo")
        assert "Python" in data.languages

    def test_collect_commits(self):
        collector = _make_collector_mock()
        data = collector.collect_all("https://github.com/owner/repo")
        assert len(data.commits) == 5
        assert data.commits[0].message.startswith("feat:")

    def test_collect_branches(self):
        collector = _make_collector_mock()
        data = collector.collect_all("https://github.com/owner/repo")
        assert "main" in data.branches
        assert "dev" in data.branches

    def test_collect_prs(self):
        collector = _make_collector_mock()
        data = collector.collect_all("https://github.com/owner/repo")
        assert data.merged_prs == 1

    def test_collect_has_dockerfile(self):
        collector = _make_collector_mock()
        data = collector.collect_all("https://github.com/owner/repo")
        assert data.has_dockerfile is True

    def test_collect_has_tests_via_dir(self):
        collector = _make_collector_mock()
        data = collector.collect_all("https://github.com/owner/repo")
        assert data.has_tests is True
        assert data.test_files_count >= 2

    def test_collect_ci_cd_via_github_dir(self):
        collector = _make_collector_mock()
        data = collector.collect_all("https://github.com/owner/repo")
        assert data.has_ci_cd is True

    def test_collect_readme(self):
        collector = _make_collector_mock()
        data = collector.collect_all("https://github.com/owner/repo")
        assert data.readme_length > 0
        assert "Title" in data.readme_content

    def test_collect_dependencies(self):
        collector = _make_collector_mock()
        data = collector.collect_all("https://github.com/owner/repo")
        assert "requirements.txt" in data.dependency_content
        assert "django" in data.dependency_content["requirements.txt"]

    def test_collect_contributors(self):
        collector = _make_collector_mock()
        data = collector.collect_all("https://github.com/owner/repo")
        assert data.contributor_count == 2

    def test_collect_all_error_on_missing_repo(self):
        collector = GitHubCollector(token="fake")
        collector._get = lambda path, params=None: None
        data = collector.collect_all("https://github.com/owner/repo")
        assert data.error is not None

    def test_collect_all_propagates_runtime_error(self):
        collector = GitHubCollector(token="fake")
        def _get_raising(path, params=None):
            raise RuntimeError("rate limit hit")
        collector._get = _get_raising
        data = collector.collect_all("https://github.com/owner/repo")
        assert "rate limit" in data.error


# ─── collector.get_user_info ───────────────────────────────────────────────────

class TestGetUserInfo:
    def test_returns_user_info(self):
        collector = GitHubCollector(token="fake")
        collector._get = lambda path, params=None: {"login": "user", "followers": 5}
        info = collector.get_user_info("user")
        assert info["login"] == "user"

    def test_raises_when_not_found(self):
        collector = GitHubCollector(token="fake")
        collector._get = lambda path, params=None: None
        with pytest.raises(RuntimeError, match="não encontrado"):
            collector.get_user_info("ghost")


# ─── collector.get_user_repos ─────────────────────────────────────────────────

class TestGetUserRepos:
    def test_returns_owned_repos(self):
        collector = GitHubCollector(token="fake")
        owned = [
            {"full_name": "user/repo1", "fork": False, "archived": False, "pushed_at": "2024-01-01"},
            {"full_name": "user/repo2", "fork": False, "archived": False, "pushed_at": "2023-01-01"},
        ]

        def _get(path, params=None):
            if "/repos" in path:
                return owned
            if "/events" in path:
                return []
            return None

        collector._get = _get
        repos = collector.get_user_repos("user", max_repos=5)
        assert len(repos) == 2

    def test_skips_forks_and_archived(self):
        collector = GitHubCollector(token="fake")
        repos_data = [
            {"full_name": "user/fork", "fork": True, "archived": False, "pushed_at": "2024-01-01"},
            {"full_name": "user/archived", "fork": False, "archived": True, "pushed_at": "2024-01-01"},
            {"full_name": "user/good", "fork": False, "archived": False, "pushed_at": "2024-01-01"},
        ]

        def _get(path, params=None):
            if "/repos" in path:
                return repos_data
            return []

        collector._get = _get
        repos = collector.get_user_repos("user", max_repos=10)
        full_names = [r["full_name"] for r in repos]
        assert "user/good" in full_names
        assert "user/fork" not in full_names
        assert "user/archived" not in full_names

    def test_includes_contributed_repos_from_events(self):
        collector = GitHubCollector(token="fake")
        events = [
            {"type": "PushEvent", "repo": {"name": "other/repo"}},
        ]
        contrib_repo = {"full_name": "other/repo", "archived": False, "pushed_at": "2024-06-01"}

        def _get(path, params=None):
            if path == "/users/user/repos":
                return []
            if path == "/users/user/events":
                return events
            if path == "/repos/other/repo":
                return contrib_repo
            return None

        collector._get = _get
        repos = collector.get_user_repos("user", max_repos=5)
        assert any(r["full_name"] == "other/repo" for r in repos)

    def test_max_repos_respected(self):
        collector = GitHubCollector(token="fake")
        many = [
            {"full_name": f"user/repo{i}", "fork": False, "archived": False, "pushed_at": f"2024-0{i % 9 + 1}-01"}
            for i in range(20)
        ]

        collector._get = lambda path, params=None: many if "/repos" in path else []
        repos = collector.get_user_repos("user", max_repos=5)
        assert len(repos) == 5


# ─── collector.get_contributed_repos ──────────────────────────────────────────

class TestGetContributedRepos:
    def test_returns_repos_from_events(self):
        collector = GitHubCollector(token="fake")
        events = [
            {"type": "PushEvent", "repo": {"name": "owner/repo1"}},
            {"type": "PullRequestEvent", "repo": {"name": "owner/repo2"}},
            {"type": "WatchEvent", "repo": {"name": "owner/repo3"}},  # ignored type
        ]
        repo_data = {"full_name": "owner/repo1", "archived": False, "pushed_at": "2024-01-01"}
        repo_data2 = {"full_name": "owner/repo2", "archived": False, "pushed_at": "2024-06-01"}

        def _get(path, params=None):
            if "/events" in path:
                return events if (params or {}).get("page", 1) == 1 else []
            if path == "/repos/owner/repo1":
                return repo_data
            if path == "/repos/owner/repo2":
                return repo_data2
            return None

        collector._get = _get
        repos = collector.get_contributed_repos("someuser", max_repos=5)
        full_names = [r["full_name"] for r in repos]
        assert "owner/repo1" in full_names
        assert "owner/repo2" in full_names
        assert len([r for r in repos if r.get("full_name") == "owner/repo3"]) == 0

    def test_deduplicates_repos(self):
        collector = GitHubCollector(token="fake")
        events = [
            {"type": "PushEvent", "repo": {"name": "owner/repo1"}},
            {"type": "PushEvent", "repo": {"name": "owner/repo1"}},  # duplicate
        ]
        repo_data = {"full_name": "owner/repo1", "archived": False, "pushed_at": "2024-01-01"}

        def _get(path, params=None):
            if "/events" in path:
                return events if (params or {}).get("page", 1) == 1 else []
            return repo_data

        collector._get = _get
        repos = collector.get_contributed_repos("someuser", max_repos=5)
        assert len(repos) == 1

    def test_skips_archived_repos(self):
        collector = GitHubCollector(token="fake")
        events = [{"type": "PushEvent", "repo": {"name": "owner/archived"}}]
        repo_data = {"full_name": "owner/archived", "archived": True, "pushed_at": "2024-01-01"}

        def _get(path, params=None):
            if "/events" in path:
                return events if (params or {}).get("page", 1) == 1 else []
            return repo_data

        collector._get = _get
        repos = collector.get_contributed_repos("someuser", max_repos=5)
        assert len(repos) == 0

    def test_returns_empty_when_no_events(self):
        collector = GitHubCollector(token="fake")
        collector._get = lambda path, params=None: []
        repos = collector.get_contributed_repos("someuser", max_repos=5)
        assert repos == []

    def test_max_repos_limit(self):
        collector = GitHubCollector(token="fake")
        events = [
            {"type": "PushEvent", "repo": {"name": f"owner/repo{i}"}}
            for i in range(20)
        ]

        def _get(path, params=None):
            if "/events" in path:
                return events if (params or {}).get("page", 1) == 1 else []
            full = path.replace("/repos/", "")
            return {"full_name": full, "archived": False, "pushed_at": "2024-01-01"}

        collector._get = _get
        repos = collector.get_contributed_repos("someuser", max_repos=3)
        assert len(repos) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
