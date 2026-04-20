#!/usr/bin/env python3
"""
GitHub Developer Profile Analyzer

Modos de uso:
  # Repositório específico
  python main.py https://github.com/owner/repo

  # Perfil de usuário (analisa todos os repositórios)
  python main.py --user https://github.com/rafaelakio
  python main.py --user rafaelakio

  # Flags opcionais
  python main.py <url> --verbose --no-ai --output report.json
"""

import argparse
import json
import sys
import os

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

load_dotenv()

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analisa repositórios GitHub e infere o perfil técnico e senioridade do desenvolvedor.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Repositório específico
  python main.py https://github.com/owner/repo

  # Perfil de usuário (analisa todos os repos)
  python main.py --user https://github.com/rafaelakio
  python main.py --user rafaelakio

  # Com flags
  python main.py https://github.com/owner/repo --verbose
  python main.py --user rafaelakio --no-ai --output report.json

Variáveis de ambiente:
  GITHUB_TOKEN       Token GitHub (aumenta o limite de 60 para 5000 req/hora)
  ANTHROPIC_API_KEY  Chave Anthropic para análise com IA
        """,
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="URL do repositório GitHub (https://github.com/owner/repo)",
    )
    parser.add_argument(
        "--user", "-u",
        metavar="USER_OR_URL",
        help="Analisa todos os repositórios de um usuário. Aceita URL de perfil ou apenas o username.",
    )
    parser.add_argument(
        "--max-repos",
        metavar="N",
        type=int,
        default=8,
        help="Número máximo de repositórios a analisar no modo --user (padrão: 8)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Output detalhado, incluindo streaming da IA",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Usa análise baseada em regras (sem IA)",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Salva o relatório em JSON",
    )
    parser.add_argument(
        "--token", "-t",
        metavar="TOKEN",
        help="Token GitHub (sobrescreve a variável GITHUB_TOKEN)",
    )
    return parser.parse_args()


def _check_token(args) -> str:
    github_token = args.token or os.getenv("GITHUB_TOKEN", "")
    if not github_token:
        console.print(
            "[yellow]⚠[/yellow] GITHUB_TOKEN não configurado. "
            "Limite de 60 req/hora. Configure para 5000/hora."
        )
    return github_token


def _make_ai_analyzer(args):
    from src.ai_analyzer import AIAnalyzer
    if args.no_ai:
        return AIAnalyzer(api_key="")
    return AIAnalyzer()


def _save_output(args, data: dict) -> None:
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]✓[/green] Relatório salvo em [bold]{args.output}[/bold]")


def run_repo_mode(args) -> int:
    """Analyze a single repository."""
    from src.collector import GitHubCollector, parse_github_url
    from src.analyzer import MetricsAnalyzer
    from src.reporter import print_all

    try:
        owner, repo = parse_github_url(args.url)
    except ValueError as e:
        console.print(f"[red]Erro:[/red] {e}")
        return 1

    github_token = _check_token(args)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), TimeElapsedColumn(),
                  console=console, transient=True) as p:
        p.add_task(f"Coletando dados de {owner}/{repo}...", total=None)
        collector = GitHubCollector(token=github_token)
        try:
            repo_data = collector.collect_all(args.url)
        except Exception as e:
            console.print(f"[red]Erro na coleta:[/red] {e}")
            return 1

    if repo_data.error:
        console.print(f"[red]Erro:[/red] {repo_data.error}")
        return 1

    console.print(f"[green]✓[/green] Dados coletados de [bold]{owner}/{repo}[/bold]")

    analyzer = MetricsAnalyzer()
    result = analyzer.analyze(repo_data)
    console.print(f"[green]✓[/green] Score composto: [bold]{result.composite_score:.0f}/100[/bold]")

    ai_analyzer = _make_ai_analyzer(args)
    if ai_analyzer.client and not args.no_ai:
        console.print("[green]✓[/green] Gerando análise com IA...")
    else:
        console.print("[yellow]⚠[/yellow] Análise baseada em regras (configure ANTHROPIC_API_KEY para IA)")

    textual = ai_analyzer.analyze(result, verbose=args.verbose)
    print_all(result, textual)

    _save_output(args, {
        **result.raw_summary,
        "textual_analysis": {
            "developer_profile": textual.developer_profile,
            "seniority_estimate": textual.seniority_estimate,
            "seniority_justification": textual.seniority_justification,
            "strengths": textual.strengths,
            "weaknesses": textual.weaknesses,
            "recommendations": textual.recommendations,
            "used_ai": textual.used_ai,
        },
    })
    return 0


def run_user_mode(args) -> int:
    """Analyze all repositories of a GitHub user."""
    from src.collector import GitHubCollector, parse_user_url
    from src.analyzer import MetricsAnalyzer, aggregate_results
    from src.reporter import print_all, print_repo_list

    try:
        username = parse_user_url(args.user)
    except ValueError as e:
        console.print(f"[red]Erro:[/red] {e}")
        return 1

    github_token = _check_token(args)
    collector = GitHubCollector(token=github_token)

    # Fetch user info and repo list
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), TimeElapsedColumn(),
                  console=console, transient=True) as p:
        p.add_task(f"Buscando repositórios de @{username}...", total=None)
        try:
            user_info = collector.get_user_info(username)
            repos = collector.get_user_repos(username, max_repos=args.max_repos)
        except RuntimeError as e:
            console.print(f"[red]Erro:[/red] {e}")
            return 1

    if not repos:
        console.print(f"[yellow]Nenhum repositório público encontrado para @{username}[/yellow]")
        return 1

    name_display = user_info.get("name") or username
    console.print(f"[green]✓[/green] Encontrados [bold]{len(repos)}[/bold] repositórios de [bold]{name_display}[/bold]")
    print_repo_list(repos)

    # Analyze each repo
    analyzer = MetricsAnalyzer()
    results = []
    failed = 0

    for i, repo in enumerate(repos, 1):
        full_name = repo["full_name"]
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), TimeElapsedColumn(),
                      console=console, transient=True) as p:
            p.add_task(f"[{i}/{len(repos)}] Analisando {full_name}...", total=None)
            try:
                repo_url = f"https://github.com/{full_name}"
                repo_data = collector.collect_all(repo_url)
                if repo_data.error:
                    console.print(f"  [yellow]⚠[/yellow] {full_name}: {repo_data.error}")
                    failed += 1
                    continue
                result = analyzer.analyze(repo_data)
                results.append(result)
                console.print(f"  [green]✓[/green] {full_name} — score: {result.composite_score:.0f}/100")
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] {full_name}: {e}")
                failed += 1

    if not results:
        console.print("[red]Não foi possível analisar nenhum repositório.[/red]")
        return 1

    if failed:
        console.print(f"[yellow]⚠[/yellow] {failed} repositório(s) ignorado(s).")

    # Aggregate
    console.print(f"\n[green]✓[/green] Agregando perfil de [bold]{len(results)}[/bold] repositórios...")
    agg = aggregate_results(results, username, user_info)

    # AI analysis
    ai_analyzer = _make_ai_analyzer(args)
    if ai_analyzer.client and not args.no_ai:
        console.print("[green]✓[/green] Gerando análise com IA...")
    else:
        console.print("[yellow]⚠[/yellow] Análise baseada em regras (configure ANTHROPIC_API_KEY para IA)")

    textual = ai_analyzer.analyze(agg, verbose=args.verbose)
    print_all(agg, textual, user_info=user_info)

    _save_output(args, {
        **agg.raw_summary,
        "textual_analysis": {
            "developer_profile": textual.developer_profile,
            "seniority_estimate": textual.seniority_estimate,
            "seniority_justification": textual.seniority_justification,
            "strengths": textual.strengths,
            "weaknesses": textual.weaknesses,
            "recommendations": textual.recommendations,
            "used_ai": textual.used_ai,
        },
    })
    return 0


def main() -> int:
    args = parse_args()

    # Detect user profile URL passed as positional arg (e.g. https://github.com/rafaelakio)
    if args.url and not args.user:
        import re
        # If the URL has only one path segment after github.com, treat it as a user profile
        if re.search(r"github\.com[/:]([^/\s]+)$", args.url.rstrip("/")):
            username_match = re.search(r"github\.com[/:]([^/\s]+)$", args.url.rstrip("/"))
            if username_match:
                console.print(
                    f"[cyan]ℹ[/cyan] '{args.url}' parece ser um perfil de usuário.\n"
                    f"  Iniciando análise de todos os repositórios de [bold]@{username_match.group(1)}[/bold]...\n"
                )
                args.user = args.url
                args.url = None

    if args.user:
        return run_user_mode(args)

    if not args.url:
        console.print("[red]Erro:[/red] Informe uma URL de repositório ou use --user para perfis.\n")
        console.print("Uso: python main.py https://github.com/owner/repo")
        console.print("     python main.py --user https://github.com/username")
        return 1

    return run_repo_mode(args)


if __name__ == "__main__":
    sys.exit(main())
