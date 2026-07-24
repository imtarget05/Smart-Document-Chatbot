"""Report generator — formats EvalReport as JSON, Markdown, or HTML."""

import json
from pathlib import Path
from typing import Optional

from .core import EvalReport


def report_to_json(report: EvalReport, path: Optional[Path] = None) -> str:
    data = report.to_dict()
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if path:
        path.write_text(text)
    return text


def report_to_markdown(report: EvalReport) -> str:
    return report.to_markdown()


def report_to_html(report: EvalReport) -> str:
    d = report.to_dict()
    results_rows = ""
    for r in d["results"]:
        status = "✅" if r["passed"] else "❌"
        metrics = "<br>".join(
            f"{'✓' if m['passed'] else '✗' if m['passed'] is False else '–'} "
            f"{m['name']}: {m['value']:.4f} (threshold: {m['threshold']})"
            for m in r["metrics"]
        )
        results_rows += f"""
        <tr>
            <td>{status}</td>
            <td>{r['case_name']}</td>
            <td>{r['score']:.4f}</td>
            <td>{r['latency_ms']:.1f}ms</td>
            <td>{metrics}</td>
            <td>{r.get('error', '') or ''}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Eval Report: {d['suite_name']}</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 1200px; margin: 2em auto; padding: 0 1em; }}
h1 {{ color: #333; }}
.summary {{ display: flex; gap: 2em; margin: 1em 0; }}
.card {{ background: #f5f5f5; border-radius: 8px; padding: 1em 1.5em; flex: 1; }}
.card .value {{ font-size: 2em; font-weight: bold; }}
.card .label {{ color: #666; font-size: 0.9em; }}
table {{ width: 100%; border-collapse: collapse; margin: 1em 0; }}
th, td {{ padding: 0.5em; text-align: left; border-bottom: 1px solid #ddd; }}
th {{ background: #f0f0f0; }}
tr:hover {{ background: #fafafa; }}
.pass {{ color: #22c55e; }}
.fail {{ color: #ef4444; }}
</style></head>
<body>
<h1>Eval Report: {d['suite_name']}</h1>
<p><strong>Run ID:</strong> {d['run_id']} | <strong>Date:</strong> {d['timestamp']}</p>
<div class="summary">
    <div class="card"><div class="value">{d['overall_score']:.4f}</div><div class="label">Overall Score</div></div>
    <div class="card"><div class="value">{d['passed_cases']}/{d['total_cases']}</div><div class="label">Pass Rate</div></div>
    <div class="card"><div class="value">{d['duration_ms']:.0f}ms</div><div class="label">Duration</div></div>
</div>
<table>
    <thead><tr><th>Status</th><th>Case</th><th>Score</th><th>Latency</th><th>Metrics</th><th>Error</th></tr></thead>
    <tbody>{results_rows}</tbody>
</table>
</body></html>"""


def aggregate_to_markdown(reports: list[EvalReport]) -> str:
    lines = ["# Aggregate Eval Report", ""]
    overall_scores = [r.overall_score for r in reports]
    if overall_scores:
        avg = sum(overall_scores) / len(overall_scores)
        lines.append(f"**Average Score:** {avg:.4f}")
        lines.append(f"**Total Suites:** {len(reports)}")
        lines.append(f"**Total Cases:** {sum(r.total_cases for r in reports)}")
        lines.append(f"**Total Passed:** {sum(r.passed_cases for r in reports)}")
        lines.append("")
        lines.append("| Suite | Score | Pass Rate | Duration |")
        lines.append("|-------|-------|-----------|----------|")
        for r in reports:
            pr = r.passed_cases / max(r.total_cases, 1) * 100
            lines.append(f"| {r.suite_name} | {r.overall_score:.4f} | {pr:.0f}% | {r.duration_ms:.0f}ms |")
    return "\n".join(lines)
