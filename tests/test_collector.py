import pytest
from src.collector import parse_github_url, parse_user_url, GitHubCollector, RepoData

def test_parse_github_url_valid():
    owner, repo = parse_github_url("https://github.com/google/guava")
    assert owner == "google"
    assert repo == "guava"

    owner, repo = parse_github_url("https://github.com/facebook/react.git")
    assert owner == "facebook"
    assert repo == "react"

def test_parse_github_url_invalid():
    with pytest.raises(ValueError, match="parece ser um perfil de usuário"):
        parse_github_url("https://github.com/octocat")

    with pytest.raises(ValueError, match="URL inválida"):
        parse_github_url("not-a-url")

def test_parse_github_url_enterprise():
    owner, repo = parse_github_url("https://github.mycompany.com/owner/repo")
    assert owner == "owner"
    assert repo == "repo"

def test_parse_user_url():
    assert parse_user_url("https://github.com/torvalds") == "torvalds"
    assert parse_user_url("torvalds") == "torvalds"
    
    with pytest.raises(ValueError):
        parse_user_url("invalid user!")

def test_is_quality_file():
    collector = GitHubCollector(token="fake")
    assert collector._is_quality_file(".eslintrc.json") is True
    assert collector._is_quality_file("pyproject.toml") is True
    assert collector._is_quality_file("random.txt") is False

def test_is_ci_file():
    collector = GitHubCollector(token="fake")
    assert collector._is_ci_file("Jenkinsfile") is True
    assert collector._is_ci_file(".travis.yml") is True
    assert collector._is_ci_file("build.sh") is False

def test_identify_file_by_name():
    collector = GitHubCollector(token="fake")
    data = RepoData(owner="o", repo="r", full_name="o/r", description=None, language=None)
    
    collector._identify_file_by_name("Dockerfile", data)
    assert data.has_dockerfile is True
    
    collector._identify_file_by_name(".gitignore", data)
    assert data.has_gitignore is True
    
    collector._identify_file_by_name("LICENSE.md", data)
    assert data.has_license is True
    
    collector._identify_file_by_name(".github/workflows", data) # Not identified by name but logic
    assert data.has_ci_cd is False # Name identification only handles direct files