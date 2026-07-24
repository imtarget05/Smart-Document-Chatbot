"""
Load / Stress Test for the Agent Service (issue #53).

This is a lightweight load test that can be run against a running agent
service to measure throughput and latency under concurrent load.

Usage:
    # Start the agent service first, then:
    python -m tests.test_load --base-url http://localhost:9000 --concurrency 10 --requests 100

    # Or via pytest (uses defaults):
    pytest tests/test_load.py -v -s

Requirements:
    pip install httpx
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Add agent dir to path
_AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(_AGENT_DIR))


async def _single_request(client, base_url: str, token: str) -> dict:
    """Send a single request and return timing info."""
    payload = {
        "query": "What is this document about?",
        "session_id": f"load-test-{os.getpid()}-{time.time()}",
        "user_id": "load-test-user",
        "document_ids": [],
    }
    headers = {"X-Internal-Token": token, "Content-Type": "application/json"}
    start = time.monotonic()
    try:
        resp = await client.post(
            f"{base_url}/v1/agent/invoke",
            json=payload,
            headers=headers,
            timeout=60,
        )
        elapsed = time.monotonic() - start
        return {
            "status_code": resp.status_code,
            "elapsed_ms": round(elapsed * 1000, 2),
            "success": resp.status_code == 200,
        }
    except Exception as exc:
        elapsed = time.monotonic() - start
        return {
            "status_code": 0,
            "elapsed_ms": round(elapsed * 1000, 2),
            "success": False,
            "error": str(exc),
        }


async def run_load_test(
    base_url: str, token: str, concurrency: int, total_requests: int
):
    """Run a concurrent load test and print statistics."""
    try:
        import httpx
    except ImportError:
        print("httpx not installed. Install with: pip install httpx")
        return

    print(f"Starting load test: {total_requests} requests, {concurrency} concurrent")
    print(f"Target: {base_url}/v1/agent/invoke")

    semaphore = asyncio.Semaphore(concurrency)
    results = []

    async with httpx.AsyncClient() as client:

        async def _worker():
            async with semaphore:
                result = await _single_request(client, base_url, token)
                results.append(result)

        tasks = [_worker() for _ in range(total_requests)]
        start = time.monotonic()
        await asyncio.gather(*tasks)
        total_elapsed = time.monotonic() - start

    # Compute statistics
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    latencies = [r["elapsed_ms"] for r in successes]

    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)
    print(f"Total requests:     {total_requests}")
    print(f"Concurrency:        {concurrency}")
    print(f"Total time:         {total_elapsed:.2f}s")
    print(f"Throughput:         {total_requests / total_elapsed:.2f} req/s")
    print(
        f"Success rate:       {len(successes)}/{total_requests} ({len(successes) / total_requests * 100:.1f}%)"
    )

    if latencies:
        latencies.sort()
        avg = sum(latencies) / len(latencies)
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)] if len(latencies) > 100 else p95
        print("\nLatency (ms):")
        print(f"  Average:  {avg:.2f}")
        print(f"  P50:      {p50:.2f}")
        print(f"  P95:      {p95:.2f}")
        print(f"  P99:      {p99:.2f}")
        print(f"  Min:      {min(latencies):.2f}")
        print(f"  Max:      {max(latencies):.2f}")

    if failures:
        print(f"\nFailures: {len(failures)}")
        error_types = {}
        for f in failures:
            err = f.get("error", f"HTTP {f['status_code']}")
            error_types[err] = error_types.get(err, 0) + 1
        for err, count in sorted(error_types.items(), key=lambda x: -x[1]):
            print(f"  {err}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Agent Service Load Test")
    parser.add_argument("--base-url", default="http://localhost:9000")
    parser.add_argument("--token", default=os.getenv("INTERNAL_SERVICE_TOKEN", ""))
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()

    if not args.token:
        print(
            "WARNING: INTERNAL_SERVICE_TOKEN not set. Requests will be rejected (401)."
        )
        print("Set it via --token or INTERNAL_SERVICE_TOKEN env var.")

    asyncio.run(
        run_load_test(args.base_url, args.token, args.concurrency, args.requests)
    )


if __name__ == "__main__":
    main()
