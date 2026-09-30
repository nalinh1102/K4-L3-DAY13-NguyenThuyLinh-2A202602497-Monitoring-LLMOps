from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


async def send_requests(label: str, count: int) -> list[httpx.Response]:
    os.environ["LANGFUSE_PROMPT_LABEL"] = label
    load_dotenv(REPO_ROOT / ".env", override=False)

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await asyncio.gather(
            *(
                client.post(
                    "/chat",
                    json={
                        "user_id": "cp2-student",
                        "session_id": f"cp2-{label}-{index + 1}",
                        "feature": "qa",
                        "message": "Explain why metrics logs and traces work together",
                    },
                )
                for index in range(count)
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a trace for a Langfuse prompt label")
    parser.add_argument("--label", required=True, choices=("baseline", "candidate", "production"))
    parser.add_argument("--count", type=int, default=1, choices=range(1, 21))
    args = parser.parse_args()

    responses = asyncio.run(send_requests(args.label, args.count))
    failed = [response for response in responses if response.status_code != 200]
    if failed:
        print(f"Request failed: {len(failed)}/{len(responses)} non-200 responses")
        return 1

    from langfuse import get_client

    get_client().flush()
    for response in responses:
        payload = response.json()
        print(
            f"label={args.label} status={response.status_code} "
            f"correlation_id={payload['correlation_id']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
