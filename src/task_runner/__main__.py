from __future__ import annotations

import argparse
import asyncio
import sys

from task_runner.config import load_config
from task_runner.daemon import Runner
from task_runner.logging_config import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Claude Code Task Runner")
    parser.add_argument(
        "-c", "--config",
        default="config.yml",
        help="Path to config file (default: config.yml)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run in watch mode: poll continuously instead of exiting after one batch",
    )
    args = parser.parse_args()

    setup_logging(args.log_level)
    config = load_config(args.config)

    if not config.github.token:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)
    if not config.anthropic_api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is required", file=sys.stderr)
        sys.exit(1)
    if not config.github.repos:
        print("Error: No repos configured", file=sys.stderr)
        sys.exit(1)

    runner = Runner(config)

    if args.watch:
        asyncio.run(runner.run_watch())
    else:
        asyncio.run(runner.run_once())


if __name__ == "__main__":
    main()
