"""Report formatters for benchmark results."""

import json
from pathlib import Path
from typing import Optional

from .benchmark_runner import BenchmarkReport


def report_to_json(report: BenchmarkReport, path: Optional[Path] = None) -> str:
    text = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    if path:
        path.write_text(text)
    return text


def report_to_markdown(report: BenchmarkReport) -> str:
    d = report.to_dict()
    lines = [
        f"# Benchmark Report: `{d['run_id']}`",
        f"**Date:** {d['timestamp']}  ",
        f"**Duration:** {d['duration_ms']:.0f}ms  ",
        "",
        "## Summary",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Queries | {d['total_queries']} |",
        f"| Pass Rate | {d['passed_queries']}/{d['total_queries']} ({d['pass_rate']*100:.1f}%) |",
        f"| Avg Latency | {d['avg_latency_ms']:.1f}ms |",
        f"| P95 Latency | {d['p95_latency_ms']:.1f}ms |",
        f"| Total Cost | ${d['total_cost_usd']:.4f} |",
        f"| Avg Cost/Query | ${d['avg_cost_per_query']:.6f} |",
        f"| Projected Monthly | ${d['projected_monthly_cost_usd']:.2f} |",
        "",
        "## Hardware Cost Estimates",
        "| Model | GPU | VRAM | GPU Monthly | Per-Query Inference | Monthly Total |",
        "|-------|-----|------|-------------|--------------------|--------------|",
    ]
    for name, est in d.get("hardware_estimates", {}).items():
        lines.append(
            f"| {name} ({est['model']}) | {est['recommended_gpu']} | "
            f"{est['vram_gb']}GB | ${est['monthly_gpu_cost_usd']} | "
            f"${est['per_query_inference_cost_usd']:.6f} | "
            f"${est['monthly_total_usd']:.2f} |"
        )
    lines.append("")
    latency = d.get("latency_summary")
    if latency:
        lines.extend([
            "## Latency Breakdown",
            "| Step | Avg (ms) | P95 (ms) | % of Total |",
            "|------|----------|----------|------------|",
        ])
        for step, metrics in latency.get("step_breakdown", {}).items():
            lines.append(
                f"| {step} | {metrics['avg_ms']} | {metrics['p95_ms']} | {metrics['pct_of_total']}% |"
            )
        lines.append("")
    lines.extend([
        "## Per-Query Results",
        "| # | Query | Latency (ms) | Cost ($) | Confidence | Passed |",
        "|---|-------|-------------|----------|------------|--------|",
    ])
    for i, q in enumerate(d.get("queries", [])):
        status = "✅" if q["passed"] else "❌"
        lines.append(
            f"| {i+1} | {q['query_text'][:50]}... | {q['latency_ms']:.1f} | "
            f"{q['cost_usd']:.6f} | {q['confidence']:.2f} | {status} |"
        )
    return "\n".join(lines)


def report_to_html(report: BenchmarkReport) -> str:
    d = report.to_dict()
    queries_rows = ""
    for i, q in enumerate(d.get("queries", [])):
        status = "✅" if q["passed"] else "❌"
        queries_rows += f"""
        <tr>
            <td>{i+1}</td>
            <td>{q['query_text'][:80]}...</td>
            <td>{q['latency_ms']:.1f}</td>
            <td>{q['cost_usd']:.6f}</td>
            <td>{q['confidence']:.2f}</td>
            <td>{status}</td>
            <td>{q.get('error', '') or ''}</td>
        </tr>"""

    hardware_rows = ""
    for name, est in d.get("hardware_estimates", {}).items():
        hardware_rows += f"""
        <tr>
            <td>{name}</td><td>{est['recommended_gpu']}</td>
            <td>{est['vram_gb']}GB</td><td>${est['monthly_gpu_cost_usd']}</td>
            <td>${est['per_query_inference_cost_usd']:.6f}</td>
            <td>${est['monthly_total_usd']:.2f}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Benchmark Report</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 1200px; margin: 2em auto; padding: 0 1em; }}
h1 {{ color: #333; }}
.summary {{ display: flex; gap: 2em; margin: 1em 0; flex-wrap: wrap; }}
.card {{ background: #f5f5f5; border-radius: 8px; padding: 1em 1.5em; flex: 1; min-width: 150px; }}
.card .value {{ font-size: 1.5em; font-weight: bold; }}
.card .label {{ color: #666; font-size: 0.9em; }}
.card.green .value {{ color: #22c55e; }}
.card.blue .value {{ color: #3b82f6; }}
.card.red .value {{ color: #ef4444; }}
table {{ width: 100%; border-collapse: collapse; margin: 1em 0; }}
th, td {{ padding: 0.5em; text-align: left; border-bottom: 1px solid #ddd; }}
th {{ background: #f0f0f0; }}
tr:hover {{ background: #fafafa; }}
h2 {{ margin-top: 2em; border-bottom: 2px solid #eee; padding-bottom: 0.3em; }}
</style></head>
<body>
<h1>Benchmark Report</h1>
<div class="summary">
    <div class="card blue"><div class="value">{d['avg_latency_ms']:.0f}ms</div><div class="label">Avg Latency</div></div>
    <div class="card blue"><div class="value">{d['p95_latency_ms']:.0f}ms</div><div class="label">P95 Latency</div></div>
    <div class="card green"><div class="value">${d['total_cost_usd']:.4f}</div><div class="label">Total Cost</div></div>
    <div class="card green"><div class="value">${d['avg_cost_per_query']:.6f}</div><div class="label">Avg Cost/Query</div></div>
    <div class="card red"><div class="value">{d['pass_rate']*100:.0f}%</div><div class="label">Pass Rate</div></div>
</div>
<h2>Hardware Cost Estimates</h2>
<table><thead><tr><th>Model</th><th>GPU</th><th>VRAM</th><th>GPU/Month</th><th>Per Query</th><th>Monthly Total</th></tr></thead>
<tbody>{hardware_rows}</tbody></table>
<h2>Per-Query Results</h2>
<table><thead><tr><th>#</th><th>Query</th><th>Latency</th><th>Cost</th><th>Confidence</th><th>Passed</th><th>Error</th></tr></thead>
<tbody>{queries_rows}</tbody></table>
</body></html>"""
