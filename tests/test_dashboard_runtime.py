from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app import dashboard as dashboard_module
from app.dashboard import build_dashboard_snapshot, load_recent_records, render_dashboard
from app.main import app


def _records() -> list[dict]:
    timestamp = datetime.now(timezone.utc).isoformat()
    common = {"ts": timestamp, "level": "info", "service": "api"}
    return [
        {**common, "event": "request_received", "correlation_id": "req-00000001"},
        {**common, "event": "request_received", "correlation_id": "req-00000002"},
        {
            **common,
            "event": "response_sent",
            "correlation_id": "req-00000001",
            "latency_ms": 1000,
            "ttft_ms": 100,
            "cost_usd": 0.01,
            "tokens_in": 100,
            "tokens_out": 50,
            "quality_score": 0.9,
            "tool_name": "retrieval",
            "tool_success": True,
        },
        {
            **common,
            "event": "request_failed",
            "correlation_id": "req-00000002",
            "error_type": "RuntimeError",
            "tool_name": "retrieval",
            "tool_success": False,
        },
    ]


def test_dashboard_snapshot_aggregates_six_operational_panels() -> None:
    snapshot = build_dashboard_snapshot(_records())

    assert snapshot["latency"]["p95_ms"] == 1000
    assert snapshot["traffic"]["request_count"] == 2
    assert snapshot["errors"]["error_rate_pct"] == 50
    assert snapshot["errors"]["retrieval_success_pct"] == 50
    assert snapshot["cost"]["total_usd"] == 0.01
    assert snapshot["tokens"]["input_total"] == 100
    assert snapshot["tokens"]["output_total"] == 50
    assert snapshot["quality"]["average_score"] == 0.9


def test_dashboard_filters_to_last_60_minutes(tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(record) for record in _records()) + "\n",
        encoding="utf-8",
    )

    assert len(load_recent_records(log_path)) == 4


def test_dashboard_html_has_six_named_panels() -> None:
    page = render_dashboard()

    for title in ("Latency", "Traffic", "Errors &amp; Retrieval", "Cost", "Tokens", "Quality"):
        assert title in page
    assert "Last 60 minutes" in page
    assert "Auto-refresh: 30 seconds" in page


def test_dashboard_routes_return_runtime_data(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(record) for record in _records()) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dashboard_module, "LOG_PATH", log_path)

    async def fetch() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/dashboard"), await client.get("/dashboard/data")

    page_response, data_response = asyncio.run(fetch())
    assert page_response.status_code == 200
    assert "Errors &amp; Retrieval" in page_response.text
    assert data_response.status_code == 200
    assert data_response.json()["traffic"]["request_count"] == 2
