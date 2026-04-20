import pytest
from src.analyzer import MetricsAnalyzer, AnalysisResult
from src.collector import RepoData, CommitInfo

@pytest.fixture
def analyzer():
    return MetricsAnalyzer()

@pytest.fixture
def base_repo_data():
    data = RepoData(owner="test", repo="repo", full_name="test/repo", description="Test repo", language="Python")
    data.languages = {"Python": 1000, "JavaScript": 500}
    data.language = "Python"
    return data

def test_analyze_languages(analyzer, base_repo_data):
    result = AnalysisResult(repo="repo", owner="test", description="")
    analyzer._analyze_languages(base_repo_data, result)
    assert result.primary_language == "Python"
    assert "python" in result.languages
    assert "javascript" in result.languages

def test_analyze_commits_metrics(analyzer, base_repo_data):
    base_repo_data.commits = [
        CommitInfo(sha="1", message="feat: add feature", date="2023-01-01T10:00:00Z"),
        CommitInfo(sha="2", message="fix: bug fix", date="2023-01-08T10:00:00Z"),
        CommitInfo(sha="3", message="wip: working", date="2023-01-15T10:00:00Z")
    ]
    result = AnalysisResult(repo="repo", owner="test", description="")
    analyzer._analyze_commits(base_repo_data, result)
    
    assert result.total_commits_sampled == 3
    # 2 conventional commits (feat, fix) / 3 = 0.66
    assert result.conventional_commit_ratio == pytest.approx(0.66, rel=1e-2)
    # 1 wip commit / 3 = 0.33
    assert result.wip_commit_ratio == pytest.approx(0.33, rel=1e-2)
    # 3 commits em 2 semanas aprox = 1.5/week
    assert result.commit_frequency_per_week > 0

def test_score_dimensions(analyzer, base_repo_data):
    # Setup data to get high scores
    base_repo_data.has_tests = True
    base_repo_data.test_files_count = 5
    base_repo_data.has_ci_cd = True
    base_repo_data.ci_cd_files = [".github/workflows/main.yml"]
    base_repo_data.readme_length = 2000 # "good" quality
    
    result = analyzer.analyze(base_repo_data)
    
    # Verificando dimensões específicas
    test_dim = next(d for d in result.dimensions if d.name == "Testing")
    assert test_dim.score >= 70 # 50 (has_tests) + 20 (files count >= 3)
    
    ci_dim = next(d for d in result.dimensions if d.name == "CI/CD & Automation")
    assert ci_dim.score >= 60

def test_profile_detection(analyzer, base_repo_data):
    # Mocking a Frontend profile
    base_repo_data.languages = {"TypeScript": 1000, "CSS": 500}
    base_repo_data.topics = ["react", "frontend"]
    
    result = analyzer.analyze(base_repo_data)
    assert "Frontend" in result.detected_profile

def test_seniority_levels(analyzer, base_repo_data):
    # Junior setup (low scores)
    base_repo_data.commits = [CommitInfo(sha="1", message="update", date="2023-01-01T00:00:00Z")]
    result_jr = analyzer.analyze(base_repo_data)
    assert result_jr.seniority == "junior"
    
    # Senior setup (high scores across all dimensions)
    base_repo_data.has_tests = True
    base_repo_data.test_files_count = 20
    base_repo_data.has_ci_cd = True
    base_repo_data.has_dockerfile = True
    base_repo_data.has_gitignore = True
    base_repo_data.readme_length = 6000
    base_repo_data.root_dirs = ["src", "tests", "docs", "infra", "scripts"] # organized
    base_repo_data.commits = [
        CommitInfo(sha=str(i), message=f"feat: new feature {i}", date="2023-01-01T00:00:00Z")
        for i in range(20)
    ]
    
    result_sr = analyzer.analyze(base_repo_data)
    # Dependendo dos pesos, deve atingir mid ou senior
    assert result_sr.seniority in ["mid-level", "senior"]