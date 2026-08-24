from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.services.telemetry_retention import (
    DEFAULT_BATCH_SIZE,
    MAX_BATCH_SIZE,
    RetentionSummary,
    purge_playback_events,
    retention_cutoff,
    validate_batch_size,
)


def batch_size_arg(value: str) -> int:
    try:
        return validate_batch_size(int(value))
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Purge raw Atlas Prime playback events older than 30 days")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="delete eligible rows; without this flag, report the eligible count only",
    )
    parser.add_argument(
        "--batch-size",
        type=batch_size_arg,
        default=DEFAULT_BATCH_SIZE,
        help=f"maximum rows deleted per transaction (default {DEFAULT_BATCH_SIZE}, maximum {MAX_BATCH_SIZE})",
    )
    return parser.parse_args()


def summary_payload(summary: RetentionSummary) -> dict[str, object]:
    return {
        "status": "applied" if summary.apply else "dry_run",
        "cutoff": summary.cutoff.isoformat(),
        "batch_size": summary.batch_size,
        "eligible_rows": summary.eligible_rows,
        "purged_rows": summary.purged_rows,
        "batches": summary.batches,
    }


async def run(*, apply: bool, batch_size: int = DEFAULT_BATCH_SIZE, now: datetime | None = None) -> RetentionSummary:
    validate_batch_size(batch_size)
    cutoff = retention_cutoff(now=now or datetime.now(timezone.utc))
    async with SessionLocal() as session:
        summary = await purge_playback_events(session, cutoff=cutoff, batch_size=batch_size, apply=apply)
    print(json.dumps(summary_payload(summary), sort_keys=True))
    return summary


def main() -> int:
    args = parse_args()
    try:
        asyncio.run(run(apply=args.apply, batch_size=args.batch_size))
    except Exception:
        print(json.dumps({"status": "error", "batch_size": args.batch_size}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
