"""
Scheduled Database Backup — Sends DB file to Telegram at midnight (12:00 AM IST).

Background asyncio task that runs alongside the main application.
Sends the SQLite database file to the configured Telegram backup channel
once daily at midnight, with stats summary in the caption.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.core.config import settings
from app.core.database import DB_PATH, create_backup

logger = logging.getLogger(__name__)

# IST offset (UTC + 5:30)
IST = timezone(timedelta(hours=5, minutes=30))

_backup_task: asyncio.Task | None = None


async def _send_db_to_telegram():
    """Send the current database file to the Telegram backup channel."""
    from app.services.telegram import telegram_service

    if not await telegram_service.connect():
        logger.error("Scheduled backup: Telegram not connected")
        return False

    if not DB_PATH.exists():
        logger.error("Scheduled backup: Database file not found")
        return False

    try:
        # Create a local backup first (validates + copies)
        backup_result = await create_backup()
        if backup_result["status"] != "success":
            logger.error(f"Scheduled backup: Local backup failed: {backup_result['message']}")
            return False

        # Read the DB file
        db_bytes = DB_PATH.read_bytes()
        db_size_kb = len(db_bytes) / 1024
        db_size_mb = db_size_kb / 1024

        # Build caption with stats
        now = datetime.now(IST)
        caption = (
            f"📦 **Scheduled Database Backup**\n"
            f"📅 {now.strftime('%B %d, %Y at %I:%M %p IST')}\n"
            f"💾 Size: {db_size_mb:.2f} MB ({db_size_kb:.0f} KB)\n"
            f"🔄 Auto-backup (midnight IST)"
        )

        # Fetch quick stats for the caption
        try:
            from app.core.database import AsyncSessionLocal
            from sqlalchemy import select, func
            from app.models.resource import Resource
            from app.models.user import User

            async with AsyncSessionLocal() as db:
                resources = (await db.execute(
                    select(func.count()).select_from(Resource).where(Resource.is_deleted == False)
                )).scalar()
                users = (await db.execute(
                    select(func.count()).select_from(User)
                )).scalar()

            caption += f"\n\n📊 **Stats:** {resources} resources, {users} users"
        except Exception:
            pass  # Stats are optional in caption

        # Send to Telegram
        channel_id = settings.telegram_backup_channel or settings.telegram_primary_channel
        if not channel_id:
            logger.error("Scheduled backup: No backup channel configured")
            return False

        filename = f"student_library_backup_{now.strftime('%Y%m%d_%H%M')}.db"

        result = await telegram_service.upload_file(
            file_bytes=db_bytes,
            filename=filename,
            caption=caption,
        )

        logger.info(
            f"✅ Scheduled backup sent to Telegram: {filename} "
            f"({db_size_mb:.2f} MB, message_id: {result['message_id']})"
        )
        return True

    except Exception as e:
        logger.error(f"Scheduled backup failed: {e}")
        return False


async def _backup_loop():
    """Background loop that sends DB backup at midnight IST every day."""
    logger.info("🕐 Scheduled backup task started (target: 12:00 AM IST daily)")

    while True:
        try:
            # Calculate seconds until next midnight IST
            now = datetime.now(IST)
            next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if next_midnight <= now:
                next_midnight += timedelta(days=1)

            wait_seconds = (next_midnight - now).total_seconds()
            hours_remaining = wait_seconds / 3600

            logger.info(
                f"🕐 Next scheduled backup in {hours_remaining:.1f} hours "
                f"(at {next_midnight.strftime('%Y-%m-%d %I:%M %p IST')})"
            )

            # Sleep until midnight
            await asyncio.sleep(wait_seconds)

            # It's midnight — send backup
            logger.info("🕐 Midnight IST — starting scheduled database backup...")
            success = await _send_db_to_telegram()

            if success:
                logger.info("✅ Midnight backup completed successfully")
            else:
                logger.error("❌ Midnight backup failed")

            # Wait 60 seconds before recalculating (to avoid double-trigger)
            await asyncio.sleep(60)

        except asyncio.CancelledError:
            logger.info("🕐 Scheduled backup task cancelled")
            break
        except Exception as e:
            logger.error(f"Scheduled backup loop error: {e}")
            # Wait 5 minutes before retrying on error
            await asyncio.sleep(300)


def start_backup_scheduler():
    """Start the background backup scheduler task."""
    global _backup_task
    _backup_task = asyncio.create_task(_backup_loop())
    return _backup_task


def stop_backup_scheduler():
    """Cancel the background backup scheduler task."""
    global _backup_task
    if _backup_task and not _backup_task.done():
        _backup_task.cancel()
        logger.info("🕐 Scheduled backup task stopped")


async def trigger_backup_now():
    """Manually trigger a backup (for bot commands or admin API)."""
    return await _send_db_to_telegram()
