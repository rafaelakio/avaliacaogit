"""Metrics analyzer: transforms raw RepoData into scored AnalysisResult."""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .collector import RepoData
from .config import (
    CONVENTIONAL_COMMIT_RE,
    FRAMEWORK_MAP,
    PROFILE_RULES,
    SCORE_WEIGHTS,
    SENIORITY_THRESHOLDS,
)


@dataclass
class ScoreDimension:
    name: str
    score: float  # 0–100
    details: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    repo: str
    owner: str
    description: Optional[str]

    # Detected content
    languages: list[str] = field(default_factory=list)
    primary_language: Optional[str] = None
    frameworks: list[str] = field(default_factory=list)
    detected_profile: str = "unknown"
    is_solo_project: bool = True

    # Commit metrics
    total_commits_sampled: int = 0
    avg_message_length: float = 0.0
    conventional_commit_ratio: float = 0.0
    commit_frequency_per_week: float = 0.0
    avg_commit_size: float = 0.0
    wip_commit_ratio: float = 0.0

    # Structure metrics
    has_tests: bool = False
    test_files_count: int = 0
    has_ci_cd: bool = False
    ci_cd_systems: list[str] = field(default_factory=list)
    has_dockerfile: bool = False
    readme_quality: str = "none"
    readme_length: int = 0
    has_contributing: bool = False
    has_changelog: bool = False
    quality_files: list[str] = field(default_factory=list)
    project_structure: str = "flat"
    branch_count: int = 1
    pr_count: int = 0

    # Scores
    dimensions: list[ScoreDimension] = field(default_factory=list)
    composite_score: float = 0.0
    complexity_level: str = "low"
    seniority: str = "junior"
    seniority_score: float = 0.0

    # Raw data summary for AI
    raw_summary: dict = field(default_factory=dict)


class MetricsAnalyzer:
    def analyze(self, data: RepoData) -> AnalysisResult:
        result = AnalysisResult(
            repo=data.repo,
            owner=data.owner,
            description=data.description,
        )

        self._analyze_languages(data, result)
        self._analyze_commits(data, result)
        self._analyze_structure(data, result)
        self._detect_frameworks(data, result)
        self._detect_profile(data, result)
        self._compute_scores(data, result)
        self._determine_seniority(result)
        self._build_raw_summary(data, result)

        return result

    def _analyze_languages(self, data: RepoData, result: AnalysisResult) -> None:
        if data.languages:
            total = sum(data.languages.values()) or 1
            sorted_langs = sorted(data.languages.items(), key=lambda x: x[1], reverse=True)
            result.languages = [lang.lower() for lang, _ in sorted_langs]
            result.primary_language = sorted_langs[0][0] if sorted_langs else data.language
        elif data.language:
            result.languages = [data.language.lower()]
            result.primary_language = data.language

    def _analyze_commits(self, data: RepoData, result: AnalysisResult) -> None:
        commits = data.commits
        if not commits:
            return

        result.total_commits_sampled = len(commits)

        # Message length
        lengths = [len(c.message) for c in commits if c.message]
        result.avg_message_length = sum(lengths) / len(lengths) if lengths else 0.0

        # Conventional commits
        conv = sum(1 for c in commits if CONVENTIONAL_COMMIT_RE.match(c.message or ""))
        result.conventional_commit_ratio = conv / len(commits)

        # WIP / low-quality commits
        wip_patterns = re.compile(r"^(wip|fix|temp|test|update|change|edit|commit|done|asdf|\.+|wtf|stuff)", re.IGNORECASE)
        wip = sum(1 for c in commits if wip_patterns.match(c.message or ""))
        result.wip_commit_ratio = wip / len(commits)

        # Commit frequency (commits per week)
        dates = []
        for c in commits:
            if c.date:
                try:
                    dt = datetime.fromisoformat(c.date.replace("Z", "+00:00"))
                    dates.append(dt)
                except Exception:
                    pass

        if len(dates) >= 2:
            dates.sort()
            span_days = max((dates[-1] - dates[0]).days, 1)
            result.commit_frequency_per_week = len(dates) / (span_days / 7)
        elif len(dates) == 1:
            result.commit_frequency_per_week = 1.0

    def _analyze_structure(self, data: RepoData, result: AnalysisResult) -> None:
        result.has_tests = data.has_tests
        result.test_files_count = data.test_files_count
        result.has_ci_cd = data.has_ci_cd
        result.ci_cd_systems = data.ci_cd_files
        result.has_dockerfile = data.has_dockerfile
        result.readme_length = data.readme_length
        result.branch_count = len(data.branches)
        result.pr_count = data.open_prs + data.merged_prs + data.closed_prs
        result.quality_files = data.quality_files

        # README quality
        if data.readme_length == 0:
            result.readme_quality = "none"
        elif data.readme_length < 300:
            result.readme_quality = "minimal"
        elif data.readme_length < 1500:
            result.readme_quality = "basic"
        elif data.readme_length < 5000:
            result.readme_quality = "good"
        else:
            result.readme_quality = "comprehensive"

        # Check quality files
        all_files_lower = [f.lower() for f in data.root_files]
        result.has_contributing = any(
            "contributing" in f for f in all_files_lower
        )
        result.has_changelog = any(
            "changelog" in f for f in all_files_lower
        )

        # Project structure assessment
        meaningful_dirs = [
            d for d in data.root_dirs
            if d.lower() not in {".git", ".github", "node_modules", ".venv", "venv", "__pycache__", ".idea", ".vscode"}
        ]
        if len(meaningful_dirs) >= 5:
            result.project_structure = "well-organized"
        elif len(meaningful_dirs) >= 3:
            result.project_structure = "organized"
        elif len(meaningful_dirs) >= 1:
            result.project_structure = "basic"
        else:
            result.project_structure = "flat"

        # Solo project detection
        result.is_solo_project = data.contributor_count <= 1

    def _detect_frameworks(self, data: RepoData, result: AnalysisResult) -> None:
        detected = set()
        combined_deps = " ".join(data.dependency_content.values()).lower()

        for key, display in FRAMEWORK_MAP.items():
            if re.search(r'\b' + re.escape(key) + r'\b', combined_deps):
                detected.add(display)

        # Topics can also indicate frameworks
        for topic in data.topics:
            for key, display in FRAMEWORK_MAP.items():
                if key in topic.lower():
                    detected.add(display)

        result.frameworks = sorted(detected)

    def _detect_profile(self, data: RepoData, result: AnalysisResult) -> None:
        lang_set = set(result.languages)
        fw_lower = {f.lower() for f in result.frameworks}
        all_topics = {t.lower() for t in data.topics}
        all_combined = lang_set | fw_lower | all_topics

        scores = {}

        # Data/ML profile
        data_keywords = {"numpy", "pandas", "scikit-learn", "tensorflow", "pytorch", "keras", "spark", "data"}
        data_score = len(data_keywords & (fw_lower | all_topics))
        if "python" in lang_set and data_score > 0:
            scores["Data Engineer / ML"] = data_score * 2

        # Mobile profile
        if lang_set & {"swift", "kotlin", "dart", "objective-c"}:
            scores["Mobile Developer"] = 5
        if fw_lower & {"react native", "flutter", "expo"}:
            scores["Mobile Developer"] = scores.get("Mobile Developer", 0) + 3

        # DevOps
        devops_keywords = {"dockerfile", "docker", "kubernetes", "terraform", "ansible", "helm"}
        devops_score = len(devops_keywords & (fw_lower | all_topics))
        if "dockerfile" in [f.lower() for f in data.root_files]:
            devops_score += 2
        if data.ci_cd_files:
            devops_score += 1
        if lang_set & {"hcl", "yaml"}:
            devops_score += 2
        if devops_score >= 3:
            scores["DevOps / SRE"] = devops_score

        # Frontend
        fe_langs = lang_set & {"javascript", "typescript", "css", "html", "scss", "sass"}
        fe_fws = fw_lower & {"react", "vue.js", "angular", "next.js", "nuxt.js", "vite", "webpack", "tailwind css"}
        fe_score = len(fe_langs) + len(fe_fws) * 2
        be_langs = lang_set & {"python", "go", "java", "rust", "php", "ruby", "c#", "scala"}
        be_fws = fw_lower & {"django", "flask", "fastapi", "spring boot", "spring", "gin", "actix-web", "ruby on rails", "laravel"}
        be_score = len(be_langs) + len(be_fws) * 2

        if fe_score > 0 and be_score > 0:
            scores["Fullstack Developer"] = fe_score + be_score
        elif fe_score > be_score and fe_score > 0:
            scores["Frontend Developer"] = fe_score
        elif be_score > 0:
            scores["Backend Developer"] = be_score

        if not scores:
            if result.primary_language:
                scores[f"{result.primary_language} Developer"] = 1

        if scores:
            result.detected_profile = max(scores, key=scores.get)
        else:
            result.detected_profile = "Software Developer"

    def _compute_scores(self, data: RepoData, result: AnalysisResult) -> None:
        result.dimensions = [
            self._score_commit_quality(result),
            self._score_testing(result),
            self._score_cicd(result),
            self._score_documentation(data, result),
            self._score_project_structure(data, result),
            self._score_frameworks(data, result),
            self._score_pr_workflow(data, result),
            self._score_issue_tracking(data, result),
        ]

        # Composite score calculation
        self._calculate_composite_score(result)
        self._evaluate_complexity(result)

    def _score_commit_quality(self, result: AnalysisResult) -> ScoreDimension:
        score = 0.0
        if result.total_commits_sampled > 0:
            score += result.conventional_commit_ratio * 40
            score += 30 if result.avg_message_length >= 50 else (15 if result.avg_message_length >= 20 else 5)
            score += 20 if result.wip_commit_ratio < 0.10 else (10 if result.wip_commit_ratio < 0.30 else 0)
            score += 10 if result.total_commits_sampled >= 20 else 5
        
        return ScoreDimension(
            "Commit Quality", min(score, 100),
            [f"Conv. Ratio: {result.conventional_commit_ratio:.0%}", f"Avg Length: {result.avg_message_length:.0f}c"]
        )

    def _score_testing(self, result: AnalysisResult) -> ScoreDimension:
        score = 0.0
        if result.has_tests:
            score += 50
        score += 30 if result.test_files_count >= 10 else (20 if result.test_files_count >= 3 else 10 if result.test_files_count >= 1 else 0)
        
        test_fws = {"pytest", "jest", "mocha", "vitest", "junit", "rspec", "testify"}
        found_test_fw = test_fws & {f.lower() for f in result.frameworks}
        if found_test_fw:
            score += 20
            
        return ScoreDimension("Testing", min(score, 100), [f"Files: {result.test_files_count}"])

    def _score_cicd(self, result: AnalysisResult) -> ScoreDimension:
        score = (60 if result.has_ci_cd else 0) + (25 if result.has_dockerfile else 0) + (15 if len(result.ci_cd_systems) >= 2 else 0)
        return ScoreDimension("CI/CD & Automation", min(score, 100), [f"Systems: {len(result.ci_cd_systems)}"])

    def _score_documentation(self, data: RepoData, result: AnalysisResult) -> ScoreDimension:
        score = 0.0
        readme_scores = {"none": 0, "minimal": 10, "basic": 30, "good": 55, "comprehensive": 70}
        score += readme_scores.get(result.readme_quality, 0)
        score += 15 if result.has_contributing else 0
        score += 10 if result.has_changelog else 0
        score += 5 if data.has_license else 0
        return ScoreDimension("Documentation Quality", min(score, 100), [f"Quality: {result.readme_quality}"])

    def _score_project_structure(self, data: RepoData, result: AnalysisResult) -> ScoreDimension:
        score = 0.0
        structure_scores = {"flat": 10, "basic": 35, "organized": 65, "well-organized": 90}
        score += structure_scores.get(result.project_structure, 10)
        score += 10 if data.has_gitignore else 0
        return ScoreDimension("Project Structure", min(score, 100), [f"Org: {result.project_structure}"])

    def _score_frameworks(self, data: RepoData, result: AnalysisResult) -> ScoreDimension:
        score = 0.0
        score += min(len(result.frameworks) * 8, 50)
        linting = {"eslint", "prettier", "black", "flake8", "mypy", "ruff", "pylint"}
        found_linting = linting & {f.lower() for f in result.frameworks}
        score += 25 if found_linting else 0
        score += 15 if len(data.dependency_content) > 0 else 0
        score += 10 if data.topics else 0
        return ScoreDimension("Framework & Tooling", min(score, 100), [f"Count: {len(result.frameworks)}"])

    def _score_pr_workflow(self, data: RepoData, result: AnalysisResult) -> ScoreDimension:
        total_prs = data.open_prs + data.merged_prs + data.closed_prs
        score = (60 if total_prs >= 20 else (40 if total_prs >= 5 else 20 if total_prs >= 1 else 0))
        score += 25 if result.branch_count >= 3 else (10 if result.branch_count >= 2 else 0)
        if total_prs > 0 and data.merged_prs / total_prs > 0.5:
            score += 15
        return ScoreDimension("PR Workflow", min(score, 100), [f"PRs: {total_prs}"])

    def _score_issue_tracking(self, data: RepoData, result: AnalysisResult) -> ScoreDimension:
        total_issues = data.open_issues_count + data.closed_issues_count
        score = (60 if total_issues >= 20 else (40 if total_issues >= 5 else 20 if total_issues >= 1 else 0))
        if total_issues > 0 and data.closed_issues_count / total_issues > 0.5:
            score += 40
        return ScoreDimension("Issue Tracking", min(score, 100), [f"Issues: {total_issues}"])

    def _calculate_composite_score(self, result: AnalysisResult) -> None:
        dim_keys = {
            "Commit": "commit_quality",
            "Testing": "testing",
            "CI/CD": "cicd",
            "Documentation": "documentation",
            "Project": "project_structure",
            "Framework": "framework_sophistication",
            "PR": "pr_workflow",
            "Issue": "issue_tracking",
        }
        composite = 0.0
        for dim in result.dimensions:
            for prefix, key in dim_keys.items():
                if dim.name.startswith(prefix):
                    composite += dim.score * SCORE_WEIGHTS.get(key, 0)
                    break
        result.composite_score = composite

    def _evaluate_complexity(self, result: AnalysisResult) -> None:
        avg_score = sum(d.score for d in result.dimensions) / len(result.dimensions)
        if avg_score >= 65:
            result.complexity_level = "high"
        elif avg_score >= 35:
            result.complexity_level = "medium"
        else:
            result.complexity_level = "low"

    def _determine_seniority(self, result: AnalysisResult) -> None:
        score = result.composite_score
        result.seniority_score = score
        if score >= SENIORITY_THRESHOLDS["mid"]:
            result.seniority = "senior"
        elif score >= SENIORITY_THRESHOLDS["junior"]:
            result.seniority = "mid-level"
        else:
            result.seniority = "junior"

    def _build_raw_summary(self, data: RepoData, result: AnalysisResult) -> None:
        result.raw_summary = {
            "repo": data.full_name,
            "description": data.description,
            "stars": data.stars,
            "forks": data.forks,
            "size_kb": data.size_kb,
            "created_at": data.created_at,
            "pushed_at": data.pushed_at,
            "contributor_count": data.contributor_count,
            "topics": data.topics,
            "languages": result.languages,
            "primary_language": result.primary_language,
            "frameworks": result.frameworks,
            "detected_profile": result.detected_profile,
            "seniority": result.seniority,
            "seniority_score": round(result.seniority_score, 1),
            "composite_score": round(result.composite_score, 1),
            "total_commits_sampled": result.total_commits_sampled,
            "conventional_commit_ratio": round(result.conventional_commit_ratio * 100, 1),
            "avg_message_length": round(result.avg_message_length, 1),
            "wip_commit_ratio": round(result.wip_commit_ratio * 100, 1),
            "commit_frequency_per_week": round(result.commit_frequency_per_week, 2),
            "has_tests": result.has_tests,
            "test_files_count": result.test_files_count,
            "has_ci_cd": result.has_ci_cd,
            "ci_cd_systems": result.ci_cd_systems,
            "has_dockerfile": result.has_dockerfile,
            "readme_quality": result.readme_quality,
            "readme_length": result.readme_length,
            "has_contributing": result.has_contributing,
            "has_changelog": result.has_changelog,
            "project_structure": result.project_structure,
            "branch_count": result.branch_count,
            "total_prs": result.pr_count,
            "merged_prs": data.merged_prs,
            "total_issues": data.open_issues_count + data.closed_issues_count,
            "closed_issues": data.closed_issues_count,
            "quality_files": result.quality_files,
            "is_solo_project": result.is_solo_project,
            "dimension_scores": {d.name: round(d.score, 1) for d in result.dimensions},
        }


def aggregate_results(results: list[AnalysisResult], username: str, user_info: dict) -> AnalysisResult:
    """
    Aggregate multiple AnalysisResult objects (from different repos of the same user)
    into a single representative profile, weighted by commit count.
    """
    if not results:
        raise ValueError("No results to aggregate.")

    weights = [max(r.total_commits_sampled, 1) for r in results]
    total_weight = sum(weights)

    def wavg(values: list[float]) -> float:
        return sum(v * w for v, w in zip(values, weights)) / total_weight

    # Merge languages
    lang_counter: Counter = Counter()
    for r in results:
        for lang in r.languages:
            lang_counter[lang] += 1
    all_langs = [lang for lang, _ in lang_counter.most_common()]

    # Merge frameworks
    fw_counter: Counter = Counter()
    for r in results:
        for fw in r.frameworks:
            fw_counter[fw] += 1
    all_frameworks = [fw for fw, _ in fw_counter.most_common()]

    # Most common profile
    profiles = [r.detected_profile for r in results]
    profile_counter: Counter = Counter(profiles)
    top_profile = profile_counter.most_common(1)[0][0]

    # Build aggregate
    agg = AnalysisResult(
        repo=f"[{len(results)} repositórios]",
        owner=username,
        description=user_info.get("bio") or f"Perfil GitHub: {username}",
    )
    agg.languages = all_langs[:8]
    agg.primary_language = all_langs[0] if all_langs else None
    agg.frameworks = all_frameworks[:15]
    agg.detected_profile = top_profile
    agg.is_solo_project = all(r.is_solo_project for r in results)
    agg.total_commits_sampled = sum(r.total_commits_sampled for r in results)
    agg.avg_message_length = wavg([r.avg_message_length for r in results])
    agg.conventional_commit_ratio = wavg([r.conventional_commit_ratio for r in results])
    agg.commit_frequency_per_week = wavg([r.commit_frequency_per_week for r in results])
    agg.wip_commit_ratio = wavg([r.wip_commit_ratio for r in results])
    agg.has_tests = any(r.has_tests for r in results)
    agg.test_files_count = sum(r.test_files_count for r in results)
    agg.has_ci_cd = any(r.has_ci_cd for r in results)
    agg.ci_cd_systems = list({s for r in results for s in r.ci_cd_systems})
    agg.has_dockerfile = any(r.has_dockerfile for r in results)
    agg.readme_quality = max(
        (r.readme_quality for r in results),
        key=lambda q: ["none", "minimal", "basic", "good", "comprehensive"].index(q),
    )
    agg.readme_length = max(r.readme_length for r in results)
    agg.has_contributing = any(r.has_contributing for r in results)
    agg.has_changelog = any(r.has_changelog for r in results)
    agg.project_structure = max(
        (r.project_structure for r in results),
        key=lambda s: ["flat", "basic", "organized", "well-organized"].index(s),
    )
    agg.branch_count = max(r.branch_count for r in results)
    agg.pr_count = sum(r.pr_count for r in results)
    agg.quality_files = list({f for r in results for f in r.quality_files})

    # Aggregate dimension scores
    dim_names = [d.name for d in results[0].dimensions]
    agg_dims = []
    for dim_name in dim_names:
        dim_scores = []
        for r in results:
            match = next((d for d in r.dimensions if d.name == dim_name), None)
            if match:
                dim_scores.append(match.score)
        if dim_scores:
            agg_score = sum(s * w for s, w in zip(dim_scores, weights[:len(dim_scores)])) / sum(weights[:len(dim_scores)])
            agg_dims.append(ScoreDimension(
                name=dim_name,
                score=agg_score,
                details=[f"Média ponderada de {len(results)} repositórios"],
            ))
    agg.dimensions = agg_dims

    agg.composite_score = wavg([r.composite_score for r in results])
    agg.seniority_score = agg.composite_score
    if agg.composite_score >= SENIORITY_THRESHOLDS["mid"]:
        agg.seniority = "senior"
    elif agg.composite_score >= SENIORITY_THRESHOLDS["junior"]:
        agg.seniority = "mid-level"
    else:
        agg.seniority = "junior"

    avg_score = sum(d.score for d in agg.dimensions) / len(agg.dimensions) if agg.dimensions else 0
    if avg_score >= 65:
        agg.complexity_level = "high"
    elif avg_score >= 35:
        agg.complexity_level = "medium"
    else:
        agg.complexity_level = "low"

    agg.raw_summary = {
        "user": username,
        "repos_analyzed": len(results),
        "repo_names": [f"{r.owner}/{r.repo}" for r in results],
        "bio": user_info.get("bio"),
        "public_repos": user_info.get("public_repos", 0),
        "followers": user_info.get("followers", 0),
        "languages": agg.languages,
        "primary_language": agg.primary_language,
        "frameworks": agg.frameworks,
        "detected_profile": agg.detected_profile,
        "seniority": agg.seniority,
        "seniority_score": round(agg.seniority_score, 1),
        "composite_score": round(agg.composite_score, 1),
        "total_commits_sampled": agg.total_commits_sampled,
        "conventional_commit_ratio": round(agg.conventional_commit_ratio * 100, 1),
        "avg_message_length": round(agg.avg_message_length, 1),
        "wip_commit_ratio": round(agg.wip_commit_ratio * 100, 1),
        "has_tests": agg.has_tests,
        "has_ci_cd": agg.has_ci_cd,
        "ci_cd_systems": agg.ci_cd_systems,
        "has_dockerfile": agg.has_dockerfile,
        "readme_quality": agg.readme_quality,
        "has_contributing": agg.has_contributing,
        "has_changelog": agg.has_changelog,
        "project_structure": agg.project_structure,
        "total_prs": agg.pr_count,
        "quality_files": agg.quality_files,
        "dimension_scores": {d.name: round(d.score, 1) for d in agg.dimensions},
    }

    return agg
