#!/usr/bin/env python3
"""
Native Python client benchmark for Geode

Usage: python benchmarks/benchmark.py --host localhost --port 3141 --workers 10 --queries 1000
"""

import argparse
import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import sys
sys.path.insert(0, '.')

from geode_client import Client


@dataclass
class WorkerResult:
    latencies: List[float]
    successful: int
    failed: int


async def run_worker(host: str, port: int, queries: int, skip_verify: bool) -> WorkerResult:
    """Run benchmark queries on a single worker."""
    latencies = []
    successful = 0
    failed = 0

    try:
        client = Client(host=host, port=port, skip_verify=skip_verify)

        async with client.connection() as conn:
            for _ in range(queries):
                start = time.perf_counter()
                try:
                    page, _ = await conn.query("RETURN 1")
                    # Consume the result
                    _ = list(page.rows)
                    latency_ms = (time.perf_counter() - start) * 1000
                    latencies.append(latency_ms)
                    successful += 1
                except Exception as e:
                    if failed < 3:
                        print(f"Query failed: {e}", file=sys.stderr)
                    failed += 1

    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        failed += queries

    return WorkerResult(latencies=latencies, successful=successful, failed=failed)


async def main():
    parser = argparse.ArgumentParser(description='Geode Python benchmark')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=3141, help='Server port')
    parser.add_argument('--workers', type=int, default=10, help='Number of workers')
    parser.add_argument('--queries', type=int, default=1000, help='Queries per worker')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--insecure', action='store_true', default=True, help='Skip TLS verification')
    args = parser.parse_args()

    start = time.perf_counter()

    # Run all workers concurrently
    tasks = [
        run_worker(args.host, args.port, args.queries, args.insecure)
        for _ in range(args.workers)
    ]
    results = await asyncio.gather(*tasks)

    duration = time.perf_counter() - start

    # Aggregate results
    all_latencies = []
    total_successful = 0
    total_failed = 0

    for result in results:
        all_latencies.extend(result.latencies)
        total_successful += result.successful
        total_failed += result.failed

    # Calculate statistics
    p50 = p95 = p99 = avg = 0.0
    if all_latencies:
        all_latencies.sort()
        p50 = all_latencies[len(all_latencies) // 2]
        p95 = all_latencies[int(len(all_latencies) * 0.95)]
        p99 = all_latencies[int(len(all_latencies) * 0.99)]
        avg = sum(all_latencies) / len(all_latencies)

    throughput = total_successful / duration if duration > 0 else 0

    if throughput >= 10000:
        status = "EXCELLENT"
    elif throughput >= 1000:
        status = "GOOD"
    elif throughput >= 100:
        status = "ACCEPTABLE"
    else:
        status = "LIMITED"

    result_data = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "duration_seconds": round(duration, 2),
        "total_queries": total_successful + total_failed,
        "successful_queries": total_successful,
        "failed_queries": total_failed,
        "throughput_qps": round(throughput, 0),
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "latency_p99_ms": round(p99, 2),
        "latency_avg_ms": round(avg, 2),
        "workers": args.workers,
        "queries_per_worker": args.queries,
        "status": status,
    }

    if args.json:
        print(json.dumps(result_data))
    else:
        print("======================================================================")
        print("PYTHON CLIENT BENCHMARK RESULTS")
        print("======================================================================")
        print(f"Duration: {result_data['duration_seconds']:.2f}s")
        print(f"Workers: {result_data['workers']}")
        print(f"Queries/worker: {result_data['queries_per_worker']}")
        print()
        print("RESULTS:")
        print(f"  Total queries:    {result_data['total_queries']}")
        print(f"  Successful:       {result_data['successful_queries']}")
        print(f"  Failed:           {result_data['failed_queries']}")
        print(f"  Throughput:       {result_data['throughput_qps']:.0f} qps")
        print()
        print("LATENCY:")
        print(f"  p50:  {result_data['latency_p50_ms']:.2f}ms")
        print(f"  p95:  {result_data['latency_p95_ms']:.2f}ms")
        print(f"  p99:  {result_data['latency_p99_ms']:.2f}ms")
        print(f"  avg:  {result_data['latency_avg_ms']:.2f}ms")
        print()
        print(f"STATUS: {result_data['status']}")
        print("======================================================================")


if __name__ == "__main__":
    asyncio.run(main())
