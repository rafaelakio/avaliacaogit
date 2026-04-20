"""AI-powered analysis using Claude API with streaming."""

import json
import os
from dataclasses import dataclass, field

import anthropic

from .analyzer import AnalysisResult


@dataclass
class TextualAnalysis:
    developer_profile: str = ""
    seniority_estimate: str = ""
    seniority_justification: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    full_text: str = ""
    used_ai: bool = False


ANALYSIS_PROMPT = """\
You are an experienced technical interviewer and software engineering expert.

Analyze the following GitHub repository metrics and generate a detailed technical profile of the developer.

## Repository Metrics
```json
{metrics_json}
```

## Your Task
Based on these metrics, provide a structured analysis in the following JSON format:

```json
{{
  "developer_profile": "A 2-3 sentence description of the probable developer profile type (e.g., backend, fullstack, mobile, data engineer). Mention the inferred specialization and key technologies.",
  "seniority_estimate": "junior | mid-level | senior",
  "seniority_justification": "2-3 sentences justifying the seniority estimate based on specific evidence from the metrics.",
  "strengths": [
    "Strength 1 with specific evidence",
    "Strength 2 with specific evidence",
    "Strength 3 with specific evidence"
  ],
  "weaknesses": [
    "Weakness 1 with context",
    "Weakness 2 with context"
  ],
  "recommendations": [
    "Concrete recommendation 1",
    "Concrete recommendation 2",
    "Concrete recommendation 3"
  ]
}}
```

Guidelines:
- Be specific and evidence-based. Reference actual metrics from the data.
- For seniority, consider: code organization, testing culture, automation, commit quality, documentation, use of tooling, PR/issue workflow.
- Be fair: a junior developer with good practices is better than a senior with poor ones.
- Strengths and weaknesses should be 3-5 items each.
- Recommendations should be actionable and prioritized.
- If the project is a solo/learning project, mention context appropriately.
- If data is limited (few commits, empty repo), acknowledge uncertainty.

Return ONLY valid JSON, no markdown code blocks, no additional text."""


class AIAnalyzer:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.client = anthropic.Anthropic(api_key=key) if key else None

    def analyze(self, result: AnalysisResult, verbose: bool = False) -> TextualAnalysis:
        if self.client is None:
            return self._fallback_analysis(result)

        try:
            return self._ai_analysis(result, verbose)
        except Exception as e:
            if verbose:
                print(f"\n[AI analysis failed: {e}. Using fallback.]\n")
            return self._fallback_analysis(result)

    def _ai_analysis(self, result: AnalysisResult, verbose: bool) -> TextualAnalysis:
        metrics_json = json.dumps(result.raw_summary, indent=2, ensure_ascii=False)
        prompt = ANALYSIS_PROMPT.format(metrics_json=metrics_json)

        if verbose:
            print("\n[Generating AI analysis...]", flush=True)

        full_text = ""
        with self.client.messages.stream(
            model="claude-opus-4-7",
            max_tokens=2048,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
            system=(
                "You are a technical expert who analyzes GitHub repositories to infer "
                "developer profiles and seniority. Respond only with valid JSON."
            ),
        ) as stream:
            for text in stream.text_stream:
                full_text += text
                if verbose:
                    print(text, end="", flush=True)

        if verbose:
            print()

        return self._parse_ai_response(full_text)

    def _parse_ai_response(self, raw: str) -> TextualAnalysis:
        """Parse the JSON response from Claude."""
        text = raw.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from within the text
            import re
            m = re.search(r'\{[\s\S]+\}', text)
            if m:
                data = json.loads(m.group(0))
            else:
                return TextualAnalysis(full_text=raw, used_ai=True)

        return TextualAnalysis(
            developer_profile=data.get("developer_profile", ""),
            seniority_estimate=data.get("seniority_estimate", ""),
            seniority_justification=data.get("seniority_justification", ""),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            recommendations=data.get("recommendations", []),
            full_text=raw,
            used_ai=True,
        )

    def _fallback_analysis(self, result: AnalysisResult) -> TextualAnalysis:
        """Rule-based fallback when AI is unavailable."""
        profile_text = (
            f"Likely a {result.detected_profile} based on languages "
            f"({', '.join(result.languages[:3]) or 'unknown'}) and "
            f"frameworks ({', '.join(result.frameworks[:3]) or 'none detected'}). "
        )
        if result.is_solo_project:
            profile_text += "This appears to be a solo project."

        seniority_text = result.seniority

        justification_parts = []
        if result.conventional_commit_ratio > 0.5:
            justification_parts.append("uses conventional commits consistently")
        if result.has_tests:
            justification_parts.append("has test coverage")
        if result.has_ci_cd:
            justification_parts.append("uses CI/CD automation")
        if result.readme_quality in ("good", "comprehensive"):
            justification_parts.append("maintains quality documentation")
        if not justification_parts:
            justification_parts.append(f"composite quality score of {result.composite_score:.0f}/100")

        justification = (
            f"Seniority estimated as {result.seniority} (score: {result.composite_score:.0f}/100). "
            f"Evidence: {'; '.join(justification_parts)}."
        )

        strengths = []
        weaknesses = []
        recommendations = []

        # Derive strengths from high-scoring dimensions
        for dim in sorted(result.dimensions, key=lambda d: d.score, reverse=True):
            if dim.score >= 60:
                strengths.append(f"{dim.name}: {dim.score:.0f}/100 — {dim.details[0] if dim.details else ''}")

        # Derive weaknesses from low-scoring dimensions
        for dim in sorted(result.dimensions, key=lambda d: d.score):
            if dim.score < 40:
                weaknesses.append(f"{dim.name}: {dim.score:.0f}/100 — {dim.details[0] if dim.details else ''}")

        # General recommendations
        if not result.has_tests:
            recommendations.append("Add automated tests and a testing framework.")
        if not result.has_ci_cd:
            recommendations.append("Set up CI/CD with GitHub Actions or similar.")
        if result.conventional_commit_ratio < 0.3:
            recommendations.append("Adopt Conventional Commits for better change tracking.")
        if result.readme_quality in ("none", "minimal"):
            recommendations.append("Write a comprehensive README with setup instructions.")
        if not result.has_contributing:
            recommendations.append("Add a CONTRIBUTING.md to document contribution guidelines.")

        if not recommendations:
            recommendations.append("Continue maintaining high code quality standards.")

        return TextualAnalysis(
            developer_profile=profile_text,
            seniority_estimate=seniority_text,
            seniority_justification=justification,
            strengths=strengths[:5],
            weaknesses=weaknesses[:5],
            recommendations=recommendations[:5],
            full_text="[Rule-based analysis — set ANTHROPIC_API_KEY for AI-powered analysis]",
            used_ai=False,
        )
