"""Sequential vs concurrent nutrition lookup benchmark CLI."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.benchmark import BenchmarkResult, run_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark sequential vs bounded-concurrent nutrition lookups."
    )
    parser.add_argument("--n", type=int, default=20, help="number of fake ingredients")
    parser.add_argument("--delay", type=float, default=0.05, help="fake provider latency seconds")
    parser.add_argument("--parallel", type=int, default=10, help="max concurrent lookups")
    parser.add_argument("--repeats", type=int, default=3, help="number of repeated runs")
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="output format",
    )
    parser.add_argument("--output", type=Path, help="optional file to write output")
    args = parser.parse_args()

    result = asyncio.run(
        run_benchmark(
            ingredient_count=args.n,
            artificial_delay_seconds=args.delay,
            max_parallel=args.parallel,
            repeats=args.repeats,
        )
    )
    output = format_result(result, args.format)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


def format_result(result: BenchmarkResult, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(result.to_dict(), indent=2)
    if output_format == "markdown":
        return result.to_markdown()
    return "\n".join(
        [
            f"N={result.ingredient_count} "
            f"delay={result.artificial_delay_seconds:.3f}s "
            f"parallel={result.max_parallel} repeats={result.repeats}",
            f"sequential_avg={result.sequential.average:.3f}s "
            f"(best={result.sequential.best:.3f}s worst={result.sequential.worst:.3f}s)",
            f"concurrent_avg={result.concurrent.average:.3f}s "
            f"(best={result.concurrent.best:.3f}s worst={result.concurrent.worst:.3f}s)",
            f"speedup={result.speedup:.2f}x",
            f"parallel_efficiency={result.efficiency_percent:.1f}%",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
