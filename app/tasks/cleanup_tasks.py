import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.database.session import AsyncSessionLocal
from app.repositories.verification_token_repository import VerificationTokenRepository
from app.tasks.celery_app import celery_app

log = logging.getLogger("app.tasks.cleanup")

# Keep a week of grace past expiry for support/abuse investigation before purging.
RETENTION_AFTER_EXPIRY = timedelta(days=7)


async def _purge_expired_tokens() -> int:
    cutoff = datetime.now(UTC) - RETENTION_AFTER_EXPIRY
    async with AsyncSessionLocal() as session:
        deleted = await VerificationTokenRepository(session).delete_expired_before(cutoff)
        await session.commit()
        return deleted


@celery_app.task(name="cleanup_expired_tokens")
def cleanup_expired_tokens() -> int:
    """Idempotent: safe to run twice, or to redeliver on a worker crash mid-task."""
    deleted = asyncio.run(_purge_expired_tokens())
    log.info("cleanup_expired_tokens_done", extra={"deleted": deleted})
    return deleted
