"""
Telegram Storage Service - File upload/download via Telegram channels
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from io import BytesIO

import uuid
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler
from pyrogram.errors import FloodWait, BadRequest

from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramStorageService:
    """Service for storing files in Telegram channels."""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.is_connected = False

        # Channel IDs
        self.primary_channel = settings.telegram_primary_channel
        self.backup_channel = settings.telegram_backup_channel

        # Connection settings
        self._lock = asyncio.Lock()

        # Strong references to fire-and-forget tasks (prevents GC mid-flight)
        self._background_tasks: set = set()
    
    async def connect(self) -> bool:
        """Initialize and connect Telegram client."""
        if self.is_connected:
            return True
        
        async with self._lock:
            if self.is_connected:
                return True
            
            if not all([
                settings.telegram_api_id,
                settings.telegram_api_hash,
                settings.telegram_bot_token,
            ]):
                logger.warning("Telegram credentials not configured")
                return False
            
            try:
                self.client = Client(
                    name="student_library_bot",
                    api_id=settings.telegram_api_id,
                    api_hash=settings.telegram_api_hash,
                    bot_token=settings.telegram_bot_token,
                    workdir="./sessions",
                    in_memory=True,  # Use in-memory session to avoid SQLite issues
                )
                
                self._setup_handlers()
                await self.client.start()
                self.is_connected = True
                logger.info("Telegram client connected successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect Telegram client: {e}")
                return False

    def _setup_handlers(self):
        """Setup bot command handlers."""
        
        async def start_handler(client, message):
            await message.reply_text(
                "👋 **Welcome to Student Resource Library Bot!** 📚\n\n"
                "I can help you find and download resources directly here.\n\n"
                "**Commands:**\n"
                "/search \u003cquery\u003e - Search for files\n"
                "/backup - Send DB backup now\n"
                "/dbstatus - Database health info\n"
                "/dbsend - Download raw DB file\n"
                "/dbinit - Replace DB with your file\n"
                "/help - Show this help message"
            )

        async def help_handler(client, message):
            await message.reply_text(
                "📚 **Help Menu**\n\n"
                "**Search & Download:**\n"
                "`/search python` - Find Python resources\n"
                "`/search calculus` - Find calculus notes\n\n"
                "**Database:**\n"
                "`/backup` - Create & send DB backup to channel\n"
                "`/dbstatus` - Show DB health, size, stats\n"
                "`/dbsend` - Send raw DB file to you\n"
                "`/dbinit` - Replace DB (reply to a .db file)\n\n"
                "**Tip:** Auto-backup runs daily at 12:00 AM IST"
            )

        async def search_handler(client, message):
            try:
                query = " ".join(message.command[1:])
                if not query:
                    await message.reply_text("🔍 Please provide a search term.\nExample: `/search python`")
                    return
                
                await message.reply_text(f"🔍 Searching for: **{query}**...")
                
                # Import here to avoid circular dependencies
                from app.models.resource import Resource
                from app.core.database import AsyncSessionLocal
                from sqlalchemy import select, or_
                
                # Search in DB (SQLAlchemy)
                q_like = f"%{query}%"
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Resource)
                        .where(
                            Resource.is_deleted == False,
                            Resource.visibility == "public",
                            or_(
                                Resource.title.ilike(q_like),
                                Resource.course_code.ilike(q_like),
                                Resource.tags_str.ilike(q_like),
                            ),
                        )
                        .limit(5)
                    )
                    resources = result.scalars().all()
                
                if not resources:
                    await message.reply_text("❌ No resources found.")
                    return
                
                response = f"📚 **Found {len(resources)} resources:**\n\n"
                for res in resources:
                    size_mb = res.file_size / (1024 * 1024)
                    response += (
                        f"📄 **{res.title}**\n"
                        f"CODE: `{res.course_code}`\n"
                        f"SIZE: `{size_mb:.1f} MB`\n"
                        f"⬇️ /get_{res.telegram_message_id}\n\n"
                    )
                
                await message.reply_text(response)
                
            except Exception as e:
                logger.error(f"Bot search error: {e}")
                await message.reply_text("⚠️ An error occurred while searching.")

        async def get_file_handler(client, message):
            try:
                # Format: /get_12345
                msg_id_str = message.text.split('_')[-1]
                if not msg_id_str.isdigit():
                    return
                
                message_id = int(msg_id_str)
                
                # Find resource to get full details
                from app.models.resource import Resource
                from app.core.database import AsyncSessionLocal
                from sqlalchemy import select
                
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Resource).where(Resource.telegram_message_id == message_id)
                    )
                    resource = result.scalar_one_or_none()
                
                caption = ""
                if resource:
                     caption = f"📄 {resource.title}\n🔗 {settings.app_url}/resources/{resource.slug}"

                wait_msg = await message.reply_text("⬇️ Fetching file...")
                
                # Forward or copy the file from the channel
                await self.client.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=self.primary_channel,
                    message_id=message_id,
                    caption=caption
                )
                
                await wait_msg.delete()
                
            except Exception as e:
                logger.error(f"Bot get file error: {e}")
                await message.reply_text("❌ Failed to retrieve file. It might have been deleted.")

        async def backup_handler(client, message):
            """Trigger immediate DB backup to Telegram channel."""
            try:
                wait_msg = await message.reply_text("📦 Creating database backup...")
                
                from app.tasks.scheduled_backup import trigger_backup_now
                success = await trigger_backup_now()
                
                await wait_msg.delete()
                
                if success:
                    await message.reply_text(
                        "✅ **Backup Complete!**\n\n"
                        "Database has been uploaded to the backup channel."
                    )
                else:
                    await message.reply_text("❌ Backup failed. Check server logs for details.")
                    
            except Exception as e:
                logger.error(f"Bot backup error: {e}")
                await message.reply_text(f"❌ Backup error: {str(e)}")

        async def dbstatus_handler(client, message):
            """Show database health and status info."""
            try:
                from app.core.database import check_db_health, DB_PATH, DB_BACKUP_PATH
                
                health = await check_db_health()
                
                db_size = health.get('file_size', 0)
                db_size_kb = db_size / 1024
                db_size_mb = db_size / (1024 * 1024)
                
                backup_size = health.get('backup_size', 0)
                backup_size_kb = backup_size / 1024
                
                status_emoji = {"healthy": "🟢", "degraded": "🟡", "critical": "🔴"}.get(health['status'], "⚪")
                
                response = (
                    f"📊 **Database Status**\n\n"
                    f"{status_emoji} Status: **{health['status'].upper()}**\n\n"
                    f"**Primary DB:**\n"
                    f"  📁 File: `{DB_PATH.name}`\n"
                    f"  💾 Size: {db_size_mb:.2f} MB ({db_size_kb:.0f} KB)\n"
                    f"  {'✅' if health['file_exists'] else '❌'} Exists\n\n"
                    f"**Backup:**\n"
                    f"  {'✅' if health['backup_exists'] else '❌'} Exists"
                    f"{f' ({backup_size_kb:.0f} KB)' if health['backup_exists'] else ''}\n\n"
                )
                
                if health.get('user_count') is not None:
                    response += f"👥 Users: {health['user_count']}\n"
                
                if health.get('issues'):
                    response += f"\n⚠️ **Issues:**\n"
                    for issue in health['issues']:
                        response += f"  • {issue}\n"
                
                response += f"\n🕐 Auto-backup: Daily at 12:00 AM IST"
                
                await message.reply_text(response)
                
            except Exception as e:
                logger.error(f"Bot dbstatus error: {e}")
                await message.reply_text(f"❌ Error getting DB status: {str(e)}")

        async def dbsend_handler(client, message):
            """Send the raw DB file directly to the owner for manual download."""
            try:
                from app.core.database import DB_PATH, create_backup
                from io import BytesIO
                from datetime import datetime, timezone, timedelta

                if not DB_PATH.exists():
                    await message.reply_text("❌ Database file not found!")
                    return

                wait_msg = await message.reply_text("📤 Creating consistent backup...")

                # Snapshot via the SQLite backup API — a raw read of the live
                # WAL file can be torn or miss recent transactions.
                backup_result = await create_backup()
                if backup_result["status"] != "success":
                    await wait_msg.edit_text(f"❌ Backup failed: {backup_result['message']}")
                    return
                db_bytes = Path(backup_result["path"]).read_bytes()
                await wait_msg.edit_text("📤 Sending database file...")
                IST = timezone(timedelta(hours=5, minutes=30))
                now = datetime.now(IST)
                
                file_stream = BytesIO(db_bytes)
                filename = f"student_library_{now.strftime('%Y%m%d_%H%M')}.db"
                file_stream.name = filename
                
                caption = (
                    f"📦 **Database File**\n"
                    f"📅 {now.strftime('%B %d, %Y %I:%M %p IST')}\n"
                    f"💾 Size: {len(db_bytes) / 1024:.0f} KB\n\n"
                    f"⚠️ **To replace the active DB:**\n"
                    f"1. Stop the server\n"
                    f"2. Replace `student_library.db` with this file\n"
                    f"3. Restart the server"
                )
                
                await self.client.send_document(
                    chat_id=message.chat.id,
                    document=file_stream,
                    file_name=filename,
                    caption=caption,
                )
                
                await wait_msg.delete()
                
            except Exception as e:
                logger.error(f"Bot dbsend error: {e}")
                await message.reply_text(f"❌ Error sending DB: {str(e)}")

        async def dbinit_handler(client, message):
            """Replace the active database with a file sent by the owner.
            
            Usage:
            1. Send a .db file to the bot
            2. Reply to that file with: /dbinit
            3. Bot asks for confirmation
            4. Reply: /dbinit confirm
            """
            try:
                from app.core.database import DB_PATH, DB_BACKUP_PATH
                from app.tasks.scheduled_backup import trigger_backup_now
                import sqlite3
                import tempfile
                
                args = message.command[1:] if len(message.command) > 1 else []
                is_confirm = len(args) > 0 and args[0].lower() == "confirm"
                
                # Must be a reply to a document message
                replied = message.reply_to_message
                if not replied or not replied.document:
                    await message.reply_text(
                        "⚠️ **Usage:** Reply to a `.db` file with `/dbinit`\n\n"
                        "**Steps:**\n"
                        "1. Send your `.db` file to this chat\n"
                        "2. Reply to that message with `/dbinit`\n"
                        "3. Confirm with `/dbinit confirm`"
                    )
                    return
                
                filename = replied.document.file_name or ""
                if not filename.endswith(".db"):
                    await message.reply_text("❌ File must be a `.db` (SQLite) file!")
                    return
                
                file_size_kb = replied.document.file_size / 1024
                file_size_mb = file_size_kb / 1024
                
                # Step 1: Confirmation prompt (if not already confirming)
                if not is_confirm:
                    current_size_kb = DB_PATH.stat().st_size / 1024 if DB_PATH.exists() else 0
                    await message.reply_text(
                        f"⚠️ **Database Replacement Warning**\n\n"
                        f"**Current DB:** {current_size_kb:.0f} KB\n"
                        f"**New file:** `{filename}` ({file_size_mb:.2f} MB)\n\n"
                        f"🔴 **This will:**\n"
                        f"• Backup current DB to Telegram\n"
                        f"• Replace `student_library.db` with your file\n"
                        f"• Reinitialize all database connections\n"
                        f"• All active sessions will be invalidated\n\n"
                        f"To proceed, reply to the same file with:\n"
                        f"`/dbinit confirm`"
                    )
                    return
                
                # Step 2: Execute replacement
                wait_msg = await message.reply_text("📦 Starting database replacement...")
                
                # 2a. Backup current DB to Telegram first
                await message.reply_text("📤 Step 1/4: Backing up current database to Telegram...")
                try:
                    await trigger_backup_now()
                except Exception as e:
                    logger.warning(f"Pre-replacement backup failed (continuing): {e}")
                
                # 2b. Download the new DB file
                await wait_msg.edit_text("⬇️ Step 2/4: Downloading new database file...")
                
                tmp_path = None
                try:
                    tmp_path = await client.download_media(
                        replied,
                        file_name=str(Path(tempfile.gettempdir()) / "new_db_temp.db")
                    )
                except Exception as e:
                    await wait_msg.edit_text(f"❌ Failed to download file: {e}")
                    return
                
                if not tmp_path or not Path(tmp_path).exists():
                    await wait_msg.edit_text("❌ Download failed — file not found.")
                    return
                
                # 2c. Validate the downloaded file
                await wait_msg.edit_text("🔍 Step 3/4: Validating SQLite file...")
                
                try:
                    conn = sqlite3.connect(tmp_path)
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA quick_check")
                    result = cursor.fetchone()
                    
                    # Count tables
                    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
                    table_count = cursor.fetchone()[0]
                    
                    # Get table names
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    conn.close()
                    
                    if result[0] != "ok":
                        await wait_msg.edit_text(f"❌ File failed integrity check: {result[0]}")
                        Path(tmp_path).unlink(missing_ok=True)
                        return
                    
                    if table_count == 0:
                        await wait_msg.edit_text("❌ File contains no tables — empty database.")
                        Path(tmp_path).unlink(missing_ok=True)
                        return
                        
                except sqlite3.DatabaseError as e:
                    await wait_msg.edit_text(f"❌ Not a valid SQLite file: {e}")
                    Path(tmp_path).unlink(missing_ok=True)
                    return
                
                # 2d. Replace the active database
                await wait_msg.edit_text("🔄 Step 4/4: Replacing active database...")
                
                try:
                    import shutil
                    from app.core.database import close_db, init_db
                    
                    # Close current DB connections
                    await close_db()
                    
                    # Backup current DB locally
                    if DB_PATH.exists():
                        shutil.copy2(str(DB_PATH), str(DB_BACKUP_PATH))
                    
                    # Replace with new file
                    shutil.copy2(tmp_path, str(DB_PATH))
                    Path(tmp_path).unlink(missing_ok=True)
                    
                    # Reinitialize database
                    await init_db()
                    
                    new_size_kb = DB_PATH.stat().st_size / 1024
                    
                    await wait_msg.edit_text(
                        f"✅ **Database Replaced Successfully!**\n\n"
                        f"📁 New DB: `{filename}`\n"
                        f"💾 Size: {new_size_kb:.0f} KB\n"
                        f"📊 Tables: {table_count} ({', '.join(tables[:8])}{'...' if len(tables) > 8 else ''})\n\n"
                        f"🔄 Database connections reinitialized.\n"
                        f"📦 Old DB backed up locally + Telegram."
                    )
                    
                except Exception as e:
                    logger.error(f"DB replacement failed: {e}")
                    # Try to restore from backup
                    try:
                        if DB_BACKUP_PATH.exists():
                            shutil.copy2(str(DB_BACKUP_PATH), str(DB_PATH))
                            await init_db()
                            await wait_msg.edit_text(
                                f"❌ Replacement failed: {e}\n\n"
                                f"🔄 Restored previous database from backup."
                            )
                        else:
                            await wait_msg.edit_text(f"❌ Replacement failed: {e}\n⚠️ No backup available!")
                    except Exception as restore_err:
                        await wait_msg.edit_text(
                            f"❌ Critical error: {e}\n"
                            f"Restore also failed: {restore_err}\n"
                            f"⚠️ Server restart required!"
                        )
                    
            except Exception as e:
                logger.error(f"Bot dbinit error: {e}")
                await message.reply_text(f"❌ Error: {str(e)}")

        # Register with Owner Filter
        # RESTRICTION: Only respond to the owner ID configured in settings.
        # No hardcoded fallback: without TELEGRAM_OWNER_ID the bot ignores
        # every command (these handlers include DB backup/replace — handing
        # those to a guessed ID would be catastrophic).
        owner_id = settings.telegram_owner_id
        if owner_id:
            owner_filter = filters.user(owner_id)
            
            self.client.add_handler(MessageHandler(start_handler, filters.command("start") & owner_filter))
            self.client.add_handler(MessageHandler(help_handler, filters.command("help") & owner_filter))
            self.client.add_handler(MessageHandler(search_handler, filters.command("search") & owner_filter))
            self.client.add_handler(MessageHandler(get_file_handler, filters.regex(r"^/get_\d+") & owner_filter))
            self.client.add_handler(MessageHandler(backup_handler, filters.command("backup") & owner_filter))
            self.client.add_handler(MessageHandler(dbstatus_handler, filters.command("dbstatus") & owner_filter))
            self.client.add_handler(MessageHandler(dbsend_handler, filters.command("dbsend") & owner_filter))
            self.client.add_handler(MessageHandler(dbinit_handler, filters.command("dbinit") & owner_filter))
        else:
            logger.warning("TELEGRAM_OWNER_ID not configured — bot command handlers disabled")
    
    async def disconnect(self):
        """Disconnect Telegram client."""
        if self.client and self.is_connected:
            await self.client.stop()
            self.is_connected = False
            logger.info("Telegram client disconnected")
    
    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        caption: str = "",
        progress_callback: Optional[callable] = None,
        _retries: int = 0,
    ) -> Dict[str, Any]:
        """
        Upload a file to the primary Telegram channel.

        Returns:
            dict with file_id, message_id, channel_id, file_size
        """
        if not await self.connect():
            raise Exception("Telegram client not connected - check credentials and network")
        
        if not self.primary_channel:
            raise Exception("Primary channel not configured")
        
        try:
            # Rate limiting: Wait before upload to avoid FloodWait
            await asyncio.sleep(2)  # 2 second delay before upload
            
            # Create BytesIO from bytes
            file_stream = BytesIO(file_bytes)
            file_stream.name = filename
            
            # Upload to primary channel
            logger.info(f"Uploading {filename} to channel {self.primary_channel}")
            message: Message = await self.client.send_document(
                chat_id=self.primary_channel,
                document=file_stream,
                file_name=filename,
                caption=caption[:1024] if caption else None,  # Telegram caption limit
                disable_notification=True,
                progress=progress_callback,
            )
            
            result = {
                "file_id": message.document.file_id,
                "message_id": message.id,
                "channel_id": self.primary_channel,
                "file_size": message.document.file_size,
                "file_name": message.document.file_name,
                "mime_type": message.document.mime_type,
            }
            
            # Schedule backup upload (non-blocking); retain a reference so the
            # task isn't garbage-collected mid-flight. The primary message id
            # is passed along so the backup copy's ids can be persisted (M12).
            if self.backup_channel:
                task = asyncio.create_task(
                    self._backup_upload(
                        file_bytes, filename, caption,
                        primary_message_id=message.id,
                        primary_channel_id=self.primary_channel,
                    )
                )
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

            logger.info(f"File uploaded successfully: {filename} ({result['file_size']} bytes, file_id: {result['file_id']})")

            # Rate limiting: Wait after upload
            await asyncio.sleep(1)  # 1 second cooldown

            return result

        except FloodWait as e:
            if _retries >= 3:
                logger.error(f"Upload failed after {_retries} FloodWait retries")
                raise Exception(f"Failed to upload to Telegram: repeated FloodWait ({e.value}s)")
            logger.warning(f"FloodWait: sleeping for {e.value} seconds (retry {_retries + 1}/3)")
            await asyncio.sleep(e.value)
            return await self.upload_file(
                file_bytes, filename, caption, progress_callback, _retries=_retries + 1
            )
        
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise Exception(f"Failed to upload to Telegram: {str(e)}")
    
    async def _persist_backup_info(
        self,
        primary_message_id: int,
        primary_channel_id: int,
        backup_file_id: str,
        backup_message_id: int,
    ):
        """Persist backup-channel message ids onto the matching resource row (M12).

        Uses its own short-lived session because this runs in a detached
        background task. Matching on message id AND channel avoids collisions
        between per-channel message id sequences. A no-op when no resource row
        matches (e.g. scheduled DB backups).
        """
        from sqlalchemy import update

        from app.core.database import async_session
        from app.models.resource import Resource

        async with async_session() as session:
            await session.execute(
                update(Resource)
                .where(
                    Resource.telegram_message_id == primary_message_id,
                    Resource.telegram_channel_id == primary_channel_id,
                )
                .values(
                    backup_telegram_file_id=backup_file_id,
                    backup_telegram_message_id=backup_message_id,
                )
            )
            await session.commit()

    async def _backup_upload(
        self,
        file_bytes: bytes,
        filename: str,
        caption: str,
        primary_message_id: Optional[int] = None,
        primary_channel_id: Optional[int] = None,
    ):
        """Upload file to backup channel (background task) and persist its ids."""
        try:
            file_stream = BytesIO(file_bytes)
            file_stream.name = filename
            
            message = await self.client.send_document(
                chat_id=self.backup_channel,
                document=file_stream,
                file_name=filename,
                caption=f"[BACKUP] {caption[:1000]}" if caption else "[BACKUP]",
                disable_notification=True,
            )
            logger.debug(f"Backup upload successful: {filename}")

            if primary_message_id is not None:
                try:
                    await self._persist_backup_info(
                        primary_message_id=primary_message_id,
                        primary_channel_id=primary_channel_id or self.primary_channel,
                        backup_file_id=message.document.file_id,
                        backup_message_id=message.id,
                    )
                except Exception:
                    # Persistence must never take down the upload task.
                    logger.exception(
                        f"Backup message ids not persisted for {filename}"
                    )
            
        except Exception as e:
            logger.error(f"Backup upload failed: {e}")
    
    async def get_file_info(
        self,
        message_id: int,
        channel_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get file information without downloading."""
        if not await self.connect():
            return None
        
        channel_id = channel_id or self.primary_channel
        
        try:
            message = await self.client.get_messages(
                chat_id=channel_id,
                message_ids=message_id,
            )
            
            if not message or not message.document:
                return None
            
            return {
                "file_id": message.document.file_id,
                "file_name": message.document.file_name,
                "file_size": message.document.file_size,
                "mime_type": message.document.mime_type,
                "date": message.date,
            }
            
        except Exception as e:
            logger.error(f"Get file info failed: {e}")
            return None
    
    async def delete_file(
        self,
        message_id: int,
        channel_id: Optional[int] = None,
        backup_message_id: Optional[int] = None,
    ) -> bool:
        """Delete a file from Telegram channel(s)."""
        if not await self.connect():
            return False
        
        channel_id = channel_id or self.primary_channel
        
        try:
            await self.client.delete_messages(
                chat_id=channel_id,
                message_ids=message_id,
            )
            
            # Also delete from backup if provided
            if backup_message_id and self.backup_channel:
                try:
                    await self.client.delete_messages(
                        chat_id=self.backup_channel,
                        message_ids=backup_message_id,
                    )
                except Exception as e:
                    logger.warning(f"Backup deletion failed: {e}")
            
            logger.info(f"File deleted: message_id={message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    async def verify_file_exists(
        self,
        message_id: int,
        channel_id: Optional[int] = None,
    ) -> bool:
        """Verify if a file still exists in the channel."""
        info = await self.get_file_info(message_id, channel_id)
        return info is not None


# Global instance
telegram_service = TelegramStorageService()
