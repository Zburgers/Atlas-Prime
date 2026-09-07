from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.db.models import ProcessingDispatch
from app.db.session import SessionLocal
from app.services.processing_dispatch import ProcessingPublicationError, publish_pending_processing_job
from app.services.processing_queue import ProcessingQueue


async def reconcile(*, limit: int = 100) -> tuple[int, int]:
    published = failed = 0
    async with SessionLocal() as session:
        dispatch_ids = list(
            (await session.scalars(
                select(ProcessingDispatch.job_id)
                .where(ProcessingDispatch.status == "pending")
                .order_by(ProcessingDispatch.created_at)
                .limit(limit)
            )).all()
        )
        for job_id in dispatch_ids:
            try:
                await publish_pending_processing_job(session, job_id, ProcessingQueue())
            except ProcessingPublicationError:
                failed += 1
            else:
                published += 1
    print(f"Published {published} pending processing dispatch(es); {failed} still pending")
    return published, failed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Republish committed but unpublished media jobs")
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(reconcile(limit=max(1, min(1000, args.limit))))
