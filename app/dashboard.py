from __future__ import annotations

import html
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from .metrics import percentile


REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))
DASHBOARD_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_recent_records(
    path: Path | None = None,
    *,
    minutes: int = 60,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    source = path or LOG_PATH
    if not source.exists():
        return []

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = current - timedelta(minutes=minutes)
    records: list[dict[str, Any]] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is not None and cutoff <= timestamp <= current + timedelta(minutes=1):
            records.append(record)
    return records


def _thresholds() -> dict[str, dict[str, Any]]:
    payload = yaml.safe_load(DASHBOARD_CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        panel["id"]: panel["threshold"]
        for panel in payload["dashboard"]["panels"]
    }


def build_dashboard_snapshot(
    records: list[dict[str, Any]], *, window_minutes: int = 60
) -> dict[str, Any]:
    request_events = [record for record in records if record.get("event") == "request_received"]
    response_events = [record for record in records if record.get("event") == "response_sent"]
    failed_events = [record for record in records if record.get("event") == "request_failed"]

    latencies = [
        int(record["latency_ms"])
        for record in response_events
        if isinstance(record.get("latency_ms"), (int, float))
    ]
    ttfts = [
        int(record["ttft_ms"])
        for record in response_events
        if isinstance(record.get("ttft_ms"), (int, float))
    ]
    costs = [
        float(record["cost_usd"])
        for record in response_events
        if isinstance(record.get("cost_usd"), (int, float))
    ]
    quality_scores = [
        float(record["quality_score"])
        for record in response_events
        if isinstance(record.get("quality_score"), (int, float))
    ]

    tool_events = [
        record
        for record in records
        if record.get("tool_name") == "retrieval"
        and isinstance(record.get("tool_success"), bool)
    ]
    retrieval_successes = sum(record["tool_success"] is True for record in tool_events)
    retrieval_success_rate = (
        retrieval_successes / len(tool_events) * 100 if tool_events else 0.0
    )
    error_rate = len(failed_events) / len(request_events) * 100 if request_events else 0.0
    error_breakdown = Counter(
        str(record.get("error_type") or "unknown") for record in failed_events
    )

    requests_by_minute: defaultdict[str, int] = defaultdict(int)
    cost_by_minute: defaultdict[str, float] = defaultdict(float)
    for record in request_events:
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is not None:
            requests_by_minute[timestamp.strftime("%H:%M")] += 1
    for record in response_events:
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is not None and isinstance(record.get("cost_usd"), (int, float)):
            cost_by_minute[timestamp.strftime("%H:%M")] += float(record["cost_usd"])

    thresholds = _thresholds()
    return {
        "window_minutes": window_minutes,
        "refresh_seconds": 30,
        "record_count": len(records),
        "latency": {
            "p50_ms": percentile(latencies, 50),
            "p95_ms": percentile(latencies, 95),
            "p99_ms": percentile(latencies, 99),
            "ttft_p95_ms": percentile(ttfts, 95),
            "threshold_ms": thresholds["latency"]["value"],
        },
        "traffic": {
            "request_count": len(request_events),
            "average_per_minute": round(len(request_events) / window_minutes, 2),
            "peak_per_minute": max(requests_by_minute.values(), default=0),
            "requests_by_minute": dict(sorted(requests_by_minute.items())),
            "threshold_per_minute": thresholds["traffic"]["value"],
        },
        "errors": {
            "failed_count": len(failed_events),
            "error_rate_pct": round(error_rate, 2),
            "error_breakdown": dict(error_breakdown),
            "retrieval_success_pct": round(retrieval_success_rate, 2),
            "error_threshold_pct": thresholds["errors"]["value"],
            "retrieval_threshold_pct": 90,
        },
        "cost": {
            "total_usd": round(sum(costs), 6),
            "average_usd": round(mean(costs), 6) if costs else 0.0,
            "cost_by_minute": {
                key: round(value, 6) for key, value in sorted(cost_by_minute.items())
            },
            "threshold_usd": thresholds["cost"]["value"],
        },
        "tokens": {
            "input_total": sum(
                int(record.get("tokens_in", 0) or 0) for record in response_events
            ),
            "output_total": sum(
                int(record.get("tokens_out", 0) or 0) for record in response_events
            ),
            "threshold_total": thresholds["tokens"]["value"],
        },
        "quality": {
            "average_score": round(mean(quality_scores), 3) if quality_scores else 0.0,
            "threshold_score": thresholds["quality"]["value"],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def dashboard_snapshot(path: Path | None = None) -> dict[str, Any]:
    return build_dashboard_snapshot(load_recent_records(path))


def _status(actual: float, threshold: float, operator: str) -> str:
    passed = actual <= threshold if operator == "lte" else actual >= threshold
    return "healthy" if passed else "alert"


def _bars(series: dict[str, int | float], *, unit: str) -> str:
    """Render a compact time series without adding a chart dependency."""
    if not series:
        return '<div class="empty-chart">No samples in this window</div>'
    recent = list(series.items())[-20:]
    maximum = max(float(value) for _, value in recent) or 1.0
    columns = "".join(
        '<div class="bar" title="{}: {} {}" style="height:{:.1f}%"></div>'.format(
            html.escape(label), value, html.escape(unit), max(float(value) / maximum * 100, 4)
        )
        for label, value in recent
    )
    return f'<div class="chart" aria-label="Values over time">{columns}</div>'


def render_dashboard(path: Path | None = None) -> str:
    data = dashboard_snapshot(path)
    latency = data["latency"]
    traffic = data["traffic"]
    errors = data["errors"]
    cost = data["cost"]
    tokens = data["tokens"]
    quality = data["quality"]
    errors_status = (
        "healthy"
        if errors["error_rate_pct"] <= errors["error_threshold_pct"]
        and errors["retrieval_success_pct"] >= errors["retrieval_threshold_pct"]
        else "alert"
    )

    panels = [
        (
            "Latency",
            _status(latency["p95_ms"], latency["threshold_ms"], "lte"),
            f"""<div class="hero">{latency['p95_ms']:.0f} ms <span>P95</span></div>
            <div class="metrics"><b>P50</b> {latency['p50_ms']:.0f} ms · <b>P99</b> {latency['p99_ms']:.0f} ms · <b>TTFT P95</b> {latency['ttft_p95_ms']:.0f} ms</div>
            <div class="threshold">SLO line: P95 ≤ {latency['threshold_ms']} ms</div>""",
        ),
        (
            "Traffic",
            _status(traffic["peak_per_minute"], traffic["threshold_per_minute"], "gte"),
            f"""<div class="hero">{traffic['request_count']} <span>requests / 60 min</span></div>
            <div class="metrics"><b>Average</b> {traffic['average_per_minute']:.2f} req/min · <b>Peak</b> {traffic['peak_per_minute']} req/min</div>
            {_bars(traffic['requests_by_minute'], unit='requests')}
            <div class="threshold">Expected activity: ≥ {traffic['threshold_per_minute']} req/min</div>""",
        ),
        (
            "Errors & Retrieval",
            errors_status,
            f"""<div class="hero">{errors['error_rate_pct']:.2f}% <span>error rate</span></div>
            <div class="metrics"><b>Failures</b> {errors['failed_count']} · <b>Retrieval success</b> {errors['retrieval_success_pct']:.2f}%<br>
            <b>Breakdown</b> {html.escape(', '.join(f'{key}: {value}' for key, value in errors['error_breakdown'].items()) or 'none')}</div>
            <div class="threshold">Error ≤ {errors['error_threshold_pct']}% · Retrieval ≥ {errors['retrieval_threshold_pct']}%</div>""",
        ),
        (
            "Cost",
            _status(cost["total_usd"], cost["threshold_usd"], "lte"),
            f"""<div class="hero">${cost['total_usd']:.6f} <span>total USD</span></div>
            <div class="metrics"><b>Average/request</b> ${cost['average_usd']:.6f}</div>
            {_bars(cost['cost_by_minute'], unit='USD')}
            <div class="threshold">Budget line: total ≤ ${cost['threshold_usd']}</div>""",
        ),
        (
            "Tokens",
            _status(
                tokens["input_total"] + tokens["output_total"],
                tokens["threshold_total"],
                "lte",
            ),
            f"""<div class="hero">{tokens['input_total'] + tokens['output_total']:,} <span>total tokens</span></div>
            <div class="metrics"><b>Input</b> {tokens['input_total']:,} · <b>Output</b> {tokens['output_total']:,}</div>
            <div class="threshold">Guardrail: total ≤ {tokens['threshold_total']:,} tokens</div>""",
        ),
        (
            "Quality",
            _status(quality["average_score"], quality["threshold_score"], "gte"),
            f"""<div class="hero">{quality['average_score']:.3f} <span>mean score</span></div>
            <div class="metrics">Heuristic quality proxy on a 0–1 scale</div>
            <div class="threshold">Quality line: mean ≥ {quality['threshold_score']}</div>""",
        ),
    ]

    cards = "".join(
        f'<section class="panel {status}"><div class="panel-title">{html.escape(title)}</div>{content}</section>'
        for title, status, content in panels
    )
    generated_at = html.escape(data["generated_at"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="30">
  <title>K4-L3B Monitoring Dashboard</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, Segoe UI, sans-serif; }}
    body {{ margin: 0; background: #08111f; color: #e8eef7; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 34px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    .subtitle {{ color: #9fb0c8; margin-bottom: 26px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 18px; }}
    .panel {{ background: #101d30; border: 1px solid #263a55; border-radius: 14px; padding: 20px; box-shadow: 0 12px 35px #02071266; }}
    .panel.healthy {{ border-top: 4px solid #42d392; }}
    .panel.alert {{ border-top: 4px solid #ff6b6b; }}
    .panel-title {{ color: #9fb0c8; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; font-size: 13px; }}
    .hero {{ font-size: 31px; font-weight: 750; margin: 18px 0 12px; }}
    .hero span {{ font-size: 14px; color: #9fb0c8; font-weight: 500; }}
    .metrics {{ line-height: 1.8; color: #d6e0ed; min-height: 58px; }}
    .threshold {{ margin-top: 14px; padding-top: 12px; border-top: 1px solid #263a55; color: #8fbaf3; font-size: 13px; }}
    .chart {{ height: 52px; display: flex; align-items: end; gap: 4px; margin: 12px 0 4px; border-bottom: 1px solid #38506f; }}
    .bar {{ flex: 1; min-width: 3px; max-width: 18px; background: linear-gradient(#67b7ff, #367ed8); border-radius: 3px 3px 0 0; }}
    .empty-chart {{ height: 52px; display: grid; place-items: center; color: #71839c; font-size: 12px; }}
    footer {{ color: #71839c; margin-top: 24px; font-size: 12px; }}
  </style>
</head>
<body>
<main>
  <h1>K4-L3B · Monitoring & LLMOps</h1>
  <div class="subtitle">Source: data/logs.jsonl · Last 60 minutes · Auto-refresh: 30 seconds · {data['record_count']} records</div>
  <div class="grid">{cards}</div>
  <footer>Generated at {generated_at} · Green = within threshold · Red = threshold breached</footer>
</main>
</body>
</html>"""
