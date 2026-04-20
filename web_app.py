#!/usr/bin/env python3
"""Flask web application for GitHub Developer Profile Analyzer."""

import csv
import io
import json
import os
import threading
import uuid

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_file

load_dotenv()

app = Flask(__name__, static_folder='templates/static')
tasks: dict = {}


def _set_progress(task_id: str, msg: str) -> None:
    if task_id in tasks:
        tasks[task_id]["progress"] = msg


def _serialize(result, textual, user_info=None, mode="repo") -> dict:
    data: dict = {
        "mode": mode,
        "owner": result.owner,
        "repo": result.repo,
        "description": result.description or "",
        "primary_language": result.primary_language or "",
        "languages": result.languages,
        "frameworks": result.frameworks,
        "detected_profile": result.detected_profile,
        "seniority": result.seniority,
        "seniority_score": round(result.seniority_score, 1),
        "composite_score": round(result.composite_score, 1),
        "complexity_level": result.complexity_level,
        "dimensions": [
            {"name": d.name, "score": round(d.score, 1), "details": d.details}
            for d in result.dimensions
        ],
        "metrics": {
            "conventional_commit_ratio": round(result.conventional_commit_ratio * 100, 1),
            "avg_message_length": round(result.avg_message_length, 1),
            "wip_commit_ratio": round(result.wip_commit_ratio * 100, 1),
            "commit_frequency_per_week": round(result.commit_frequency_per_week or 0, 2),
            "total_commits_sampled": result.total_commits_sampled,
            "has_tests": result.has_tests,
            "test_files_count": result.test_files_count,
            "has_ci_cd": result.has_ci_cd,
            "ci_cd_systems": result.ci_cd_systems,
            "has_dockerfile": result.has_dockerfile,
            "readme_quality": result.readme_quality,
            "readme_length": result.readme_length,
            "project_structure": result.project_structure,
            "pr_count": result.pr_count,
            "branch_count": result.branch_count,
            "quality_files": result.quality_files,
            "has_contributing": result.has_contributing,
            "has_changelog": result.has_changelog,
            "stars": result.raw_summary.get("stars", 0),
            "forks": result.raw_summary.get("forks", 0),
        },
        "analysis": {
            "developer_profile": textual.developer_profile,
            "seniority_estimate": textual.seniority_estimate,
            "seniority_justification": textual.seniority_justification,
            "strengths": textual.strengths,
            "weaknesses": textual.weaknesses,
            "recommendations": textual.recommendations,
            "used_ai": textual.used_ai,
        },
    }
    if mode == "user":
        info = user_info or {}
        data.update({
            "user_name": info.get("name") or result.owner,
            "user_bio": info.get("bio") or "",
            "user_followers": info.get("followers", 0),
            "user_avatar": info.get("avatar_url") or "",
            "repos_analyzed": result.raw_summary.get("repos_analyzed", 0),
            "repo_names": result.raw_summary.get("repo_names", []),
        })
    return data


def _run_repo_task(task_id: str, url: str, no_ai: bool, token: str) -> None:
    try:
        from src.collector import GitHubCollector, parse_github_url
        from src.analyzer import MetricsAnalyzer
        from src.ai_analyzer import AIAnalyzer

        _set_progress(task_id, "Validando URL...")
        owner, repo_name = parse_github_url(url)

        _set_progress(task_id, f"Coletando dados de {owner}/{repo_name}...")
        collector = GitHubCollector(token=token)
        repo_data = collector.collect_all(url)

        if repo_data.error:
            tasks[task_id] = {"status": "error", "message": repo_data.error}
            return

        _set_progress(task_id, "Calculando métricas...")
        result = MetricsAnalyzer().analyze(repo_data)

        _set_progress(task_id, "Gerando análise textual...")
        ai = AIAnalyzer(api_key="" if no_ai else None)
        textual = ai.analyze(result)

        tasks[task_id] = {"status": "done", "result": _serialize(result, textual, mode="repo")}
    except Exception as e:
        tasks[task_id] = {"status": "error", "message": str(e)}


def _run_user_task(task_id: str, user_input: str, max_repos: int, no_ai: bool, token: str) -> None:
    try:
        from src.collector import GitHubCollector, parse_user_url
        from src.analyzer import MetricsAnalyzer, aggregate_results
        from src.ai_analyzer import AIAnalyzer

        _set_progress(task_id, "Validando usuário...")
        username = parse_user_url(user_input)

        _set_progress(task_id, f"Buscando repositórios de @{username}...")
        collector = GitHubCollector(token=token)
        user_info = collector.get_user_info(username)
        repos = collector.get_user_repos(username, max_repos=max_repos)

        if not repos:
            tasks[task_id] = {
                "status": "error",
                "message": f"Nenhum repositório público encontrado para @{username}",
            }
            return

        analyzer = MetricsAnalyzer()
        results = []
        failed = 0

        for i, repo in enumerate(repos, 1):
            full_name = repo["full_name"]
            _set_progress(task_id, f"[{i}/{len(repos)}] Analisando {full_name}...")
            try:
                repo_data = collector.collect_all(f"https://github.com/{full_name}")
                if repo_data.error:
                    failed += 1
                else:
                    results.append(analyzer.analyze(repo_data))
            except Exception:
                failed += 1

        if not results:
            tasks[task_id] = {"status": "error", "message": "Não foi possível analisar nenhum repositório."}
            return

        _set_progress(task_id, f"Agregando perfil de {len(results)} repositórios...")
        agg = aggregate_results(results, username, user_info)

        _set_progress(task_id, "Gerando análise textual...")
        ai = AIAnalyzer(api_key="" if no_ai else None)
        textual = ai.analyze(agg)

        tasks[task_id] = {
            "status": "done",
            "result": _serialize(agg, textual, user_info=user_info, mode="user"),
            "failed_repos": failed,
        }
    except Exception as e:
        tasks[task_id] = {"status": "error", "message": str(e)}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    body = request.get_json(force=True) or {}
    mode = body.get("mode", "repo")
    no_ai = bool(body.get("no_ai", False))
    token = body.get("token") or os.getenv("GITHUB_TOKEN", "")
    max_repos = min(int(body.get("max_repos", 8)), 30)

    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "running", "progress": "Iniciando..."}

    if mode == "user":
        t = threading.Thread(
            target=_run_user_task,
            args=(task_id, body.get("user", ""), max_repos, no_ai, token),
            daemon=True,
        )
    else:
        t = threading.Thread(
            target=_run_repo_task,
            args=(task_id, body.get("url", ""), no_ai, token),
            daemon=True,
        )
    t.start()
    return jsonify({"task_id": task_id})


@app.route("/api/status/<task_id>")
def get_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"status": "not_found"}), 404
    return jsonify(task)


@app.route("/api/export/<task_id>/json")
def export_json(task_id: str):
    task = tasks.get(task_id)
    if not task or task["status"] != "done":
        return jsonify({"error": "Resultado não disponível"}), 400
    buf = io.BytesIO(json.dumps(task["result"], indent=2, ensure_ascii=False).encode())
    buf.seek(0)
    return send_file(buf, mimetype="application/json", as_attachment=True, download_name="analysis.json")


@app.route("/api/export/<task_id>/csv")
def export_csv(task_id: str):
    task = tasks.get(task_id)
    if not task or task["status"] != "done":
        return jsonify({"error": "Resultado não disponível"}), 400

    r = task["result"]
    buf = io.StringIO()
    w = csv.writer(buf)

    w.writerow(["GitHub Developer Profile Analysis"])
    w.writerow(["Owner/User", r["owner"]])
    if r["mode"] == "repo":
        w.writerow(["Repository", r["repo"]])
    else:
        w.writerow(["Repos Analyzed", r.get("repos_analyzed", "")])
    w.writerow(["Profile", r["detected_profile"]])
    w.writerow(["Seniority", r["seniority"]])
    w.writerow(["Composite Score", r["composite_score"]])
    w.writerow(["Primary Language", r["primary_language"]])
    w.writerow([])
    w.writerow(["Languages"])
    w.writerow(r["languages"])
    w.writerow(["Frameworks"])
    w.writerow(r["frameworks"])
    w.writerow([])
    w.writerow(["Score Dimensions"])
    w.writerow(["Dimension", "Score"])
    for d in r["dimensions"]:
        w.writerow([d["name"], d["score"]])
    w.writerow([])
    w.writerow(["Metrics"])
    w.writerow(["Metric", "Value"])
    for k, v in r["metrics"].items():
        w.writerow([k, ", ".join(str(x) for x in v) if isinstance(v, list) else v])
    w.writerow([])
    an = r["analysis"]
    w.writerow(["Textual Analysis"])
    w.writerow(["Developer Profile", an["developer_profile"]])
    w.writerow(["Seniority Estimate", an["seniority_estimate"]])
    w.writerow(["Seniority Justification", an["seniority_justification"]])
    w.writerow([])
    w.writerow(["Strengths"])
    for s in an["strengths"]:
        w.writerow([s])
    w.writerow(["Areas for Improvement"])
    for x in an["weaknesses"]:
        w.writerow([x])
    w.writerow(["Recommendations"])
    for rec in an["recommendations"]:
        w.writerow([rec])

    return Response(
        buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=analysis.csv"},
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
