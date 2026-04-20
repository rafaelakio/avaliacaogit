"""Rich terminal reporter: prints the metrics table and textual analysis."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from .analyzer import AnalysisResult
from .ai_analyzer import TextualAnalysis

console = Console()


def _seniority_color(s: str) -> str:
    return {"junior": "yellow", "mid-level": "cyan", "senior": "green"}.get(s, "white")


def _score_color(score: float) -> str:
    if score >= 70:
        return "green"
    if score >= 40:
        return "yellow"
    return "red"


def _score_bar(score: float, width: int = 20) -> str:
    filled = int((score / 100) * width)
    return "█" * filled + "░" * (width - filled)


def print_header(result: AnalysisResult, user_info: dict | None = None) -> None:
    scolor = _seniority_color(result.seniority)
    header = Text()
    is_user_mode = user_info is not None

    if is_user_mode:
        name = user_info.get("name") or result.owner
        header.append(f"  {name} (@{result.owner})\n", style="bold white")
        repos_analyzed = result.raw_summary.get("repos_analyzed", "?")
        header.append(f"  {repos_analyzed} repositórios analisados\n", style="dim")
        if result.description:
            header.append(f"  {result.description}\n", style="dim italic")
    else:
        header.append(f"  {result.owner}/{result.repo}\n", style="bold white")
        if result.description:
            header.append(f"  {result.description}\n", style="dim")

    header.append(f"\n  Profile: ", style="white")
    header.append(result.detected_profile, style="bold cyan")
    header.append("   |   Seniority: ", style="white")
    header.append(result.seniority.upper(), style=f"bold {scolor}")
    header.append(f"  ({result.seniority_score:.0f}/100)", style="dim")
    title = "[bold blue]GitHub User Profile Analysis[/bold blue]" if is_user_mode else "[bold blue]GitHub Repository Analysis[/bold blue]"
    console.print(Panel(header, title=title, box=box.ROUNDED))


def print_metrics_table(result: AnalysisResult) -> None:
    # ── Main Metrics ──────────────────────────────────────────────────
    table = Table(
        title="[bold]Repository Metrics[/bold]",
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("Metric", style="cyan", width=32)
    table.add_column("Value", style="white")
    table.add_column("Details", style="dim")

    # Languages
    langs_str = ", ".join(result.languages[:5]) or "–"
    table.add_row("Languages", langs_str, f"Primary: {result.primary_language or '–'}")

    # Frameworks
    fw_str = ", ".join(result.frameworks[:6]) if result.frameworks else "none detected"
    table.add_row("Frameworks & Libraries", fw_str[:60], f"{len(result.frameworks)} total")

    # Commits
    table.add_row(
        "Commit Quality",
        f"{result.conventional_commit_ratio:.0%} conventional",
        f"avg {result.avg_message_length:.0f} chars, {result.wip_commit_ratio:.0%} vague",
    )
    freq = f"{result.commit_frequency_per_week:.1f}/week" if result.commit_frequency_per_week else "–"
    table.add_row(
        "Commit Frequency",
        freq,
        f"{result.total_commits_sampled} commits sampled",
    )

    # Tests
    test_val = "✓ Yes" if result.has_tests else "✗ No"
    test_color = "green" if result.has_tests else "red"
    table.add_row(
        "Automated Tests",
        f"[{test_color}]{test_val}[/{test_color}]",
        f"{result.test_files_count} test file(s) found",
    )

    # CI/CD
    ci_val = "✓ Yes" if result.has_ci_cd else "✗ No"
    ci_color = "green" if result.has_ci_cd else "red"
    ci_detail = ", ".join(result.ci_cd_systems[:3]) or "–"
    table.add_row(
        "CI/CD Automation",
        f"[{ci_color}]{ci_val}[/{ci_color}]",
        ci_detail,
    )

    # Dockerfile
    docker_val = "✓ Yes" if result.has_dockerfile else "✗ No"
    docker_color = "green" if result.has_dockerfile else "dim"
    table.add_row("Containerization", f"[{docker_color}]{docker_val}[/{docker_color}]", "Dockerfile / Compose")

    # Documentation
    readme_color = {"none": "red", "minimal": "yellow", "basic": "yellow", "good": "green", "comprehensive": "bold green"}.get(result.readme_quality, "white")
    table.add_row(
        "Documentation (README)",
        f"[{readme_color}]{result.readme_quality.capitalize()}[/{readme_color}]",
        f"{result.readme_length:,} characters",
    )
    has_contrib = "✓" if result.has_contributing else "✗"
    has_change = "✓" if result.has_changelog else "✗"
    table.add_row(
        "Supporting Docs",
        f"CONTRIBUTING: {has_contrib}  |  CHANGELOG: {has_change}",
        "",
    )

    # Project structure
    struct_color = {"flat": "red", "basic": "yellow", "organized": "green", "well-organized": "bold green"}.get(result.project_structure, "white")
    table.add_row(
        "Project Structure",
        f"[{struct_color}]{result.project_structure.capitalize()}[/{struct_color}]",
        f"Complexity: {result.complexity_level}",
    )

    # PRs & Issues
    table.add_row(
        "PR Workflow",
        f"{result.pr_count} PRs",
        f"Branches: {result.branch_count}",
    )

    # Quality files
    qf = ", ".join(result.quality_files[:4]) if result.quality_files else "none"
    table.add_row("Good Practices Files", qf[:60], f"{len(result.quality_files)} detected")

    console.print()
    console.print(table)

    # ── Score Dimensions ──────────────────────────────────────────────
    score_table = Table(
        title="[bold]Quality Score Breakdown[/bold]",
        box=box.SIMPLE_HEAVY,
        header_style="bold magenta",
        expand=True,
    )
    score_table.add_column("Dimension", style="cyan", width=28)
    score_table.add_column("Score", width=8)
    score_table.add_column("Bar", width=22)
    score_table.add_column("Top Detail", style="dim")

    for dim in result.dimensions:
        color = _score_color(dim.score)
        bar = _score_bar(dim.score)
        detail = dim.details[0] if dim.details else ""
        score_table.add_row(
            dim.name,
            f"[{color}]{dim.score:.0f}[/{color}]",
            f"[{color}]{bar}[/{color}]",
            detail,
        )

    # Composite
    comp_color = _score_color(result.composite_score)
    score_table.add_row(
        "[bold]COMPOSITE SCORE[/bold]",
        f"[bold {comp_color}]{result.composite_score:.0f}[/bold {comp_color}]",
        f"[bold {comp_color}]{_score_bar(result.composite_score)}[/bold {comp_color}]",
        f"Seniority: {result.seniority}",
    )

    console.print(score_table)


def print_analysis(analysis: TextualAnalysis) -> None:
    source = "[AI-powered]" if analysis.used_ai else "[Rule-based — add ANTHROPIC_API_KEY for AI analysis]"
    title = f"[bold blue]Developer Analysis[/bold blue]  [dim]{source}[/dim]"

    content = Text()

    # Profile
    content.append("DEVELOPER PROFILE\n", style="bold yellow")
    content.append(f"{analysis.developer_profile}\n\n", style="white")

    # Seniority
    content.append("SENIORITY ESTIMATE\n", style="bold yellow")
    scolor = _seniority_color(analysis.seniority_estimate)
    content.append(f"{analysis.seniority_estimate.upper()}\n", style=f"bold {scolor}")
    content.append(f"{analysis.seniority_justification}\n\n", style="white")

    # Strengths
    if analysis.strengths:
        content.append("STRENGTHS\n", style="bold green")
        for s in analysis.strengths:
            content.append(f"  ✓ {s}\n", style="green")
        content.append("\n")

    # Weaknesses
    if analysis.weaknesses:
        content.append("AREAS FOR IMPROVEMENT\n", style="bold red")
        for w in analysis.weaknesses:
            content.append(f"  ✗ {w}\n", style="red")
        content.append("\n")

    # Recommendations
    if analysis.recommendations:
        content.append("RECOMMENDATIONS\n", style="bold cyan")
        for i, r in enumerate(analysis.recommendations, 1):
            content.append(f"  {i}. {r}\n", style="cyan")

    console.print(Panel(content, title=title, box=box.ROUNDED, padding=(1, 2)))


def print_repo_list(repos: list[dict]) -> None:
    """Print a summary table of repos being analyzed."""
    table = Table(
        title="[bold]Repositórios Encontrados[/bold]",
        box=box.SIMPLE_HEAVY,
        header_style="bold magenta",
    )
    table.add_column("#", width=4, style="dim")
    table.add_column("Repositório", style="cyan")
    table.add_column("Linguagem", style="white", width=14)
    table.add_column("Stars", width=7)
    table.add_column("Atualizado", style="dim", width=12)

    for i, repo in enumerate(repos, 1):
        pushed = (repo.get("pushed_at") or "")[:10]
        table.add_row(
            str(i),
            repo.get("full_name", ""),
            repo.get("language") or "–",
            str(repo.get("stargazers_count", 0)),
            pushed,
        )
    console.print()
    console.print(table)


def print_all(result: AnalysisResult, analysis: TextualAnalysis, user_info: dict | None = None) -> None:
    console.print()
    print_header(result, user_info=user_info)
    print_metrics_table(result)
    print_analysis(analysis)
    console.print()
