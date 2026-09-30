from __future__ import annotations

import asyncio
import re

import httpx

from app.main import app


def _post_chat(headers: dict[str, str] | None = None) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                headers=headers,
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Explain observability",
                },
            )

    return asyncio.run(send_request())


def test_middleware_generates_and_returns_correlation_id() -> None:
    response = _post_chat()

    assert response.status_code == 200
    correlation_id = response.headers["x-request-id"]
    assert re.fullmatch(r"req-[0-9a-f]{8}", correlation_id)
    assert response.json()["correlation_id"] == correlation_id
    assert float(response.headers["x-response-time-ms"]) >= 0


def test_middleware_accepts_valid_incoming_request_id() -> None:
    response = _post_chat({"x-request-id": "req-ABCDEF12"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-ABCDEF12"
    assert response.json()["correlation_id"] == "req-ABCDEF12"


def test_middleware_replaces_invalid_incoming_request_id() -> None:
    response = _post_chat({"x-request-id": "not-a-valid-id"})

    assert response.status_code == 200
    assert re.fullmatch(r"req-[0-9a-f]{8}", response.headers["x-request-id"])
