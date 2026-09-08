from __future__ import annotations

import argparse
import asyncio
from datetime import date

from app.db.session import SessionLocal
from app.services.analytics import rebuild_daily_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild Atlas Prime daily analytics from raw events")
    parser.add_argument("--date-from", type=date.fromisoformat, required=True)
    parser.add_argument("--date-to", type=date.fromisoformat, required=True)
    return parser.parse_args()


async def run(date_from: date, date_to: date) -> None:
    async with SessionLocal() as session:
        result = await rebuild_daily_metrics(session, date_from=date_from, date_to=date_to)
    print(
        f"Rebuilt daily metrics {result.date_from}..{result.date_to}: "
        f"{result.video_metric_rows} video rows, {result.creator_metric_rows} creator rows"
    )


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.date_from, args.date_to))
