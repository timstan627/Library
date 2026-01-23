"""
Telegram Storage Service - File upload/download via Telegram channels
"""
import asyncio
import logging
from typing import Optional, AsyncIterator, Dict, Any
from io import BytesIO

import uuid
import os
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler
from pyrogram.errors import FloodWait, BadRequest

from app.core.config import settings
from app.services.cache import cache_service

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
                "/search <query> - Search for files\n"
                "/help - Show this help message"
            )

        async def help_handler(client, message):
            await message.reply_text(
                "📚 **Help Menu**\n\n"
                "**Search:**\n"
                "`/search python` - Find Python resources\n"
                "`/search calculus` - Find calculus notes\n\n"
                "Tap 'Download' on any result to get the file!"
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
                
                # Search in DB
                regex = {"$regex": query, "$options": "i"}
                resources = await Resource.find(
                    {
                        "$or": [
                            {"title": regex},
                            {"course_code": regex},
                            {"tags": regex}
                        ],
                        "is_deleted": False,
                        "visibility": "public"  # Only public resources via bot
                    }
                ).limit(5).to_list()
                
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
                
                # Find resource to get full details (optional, but good for caption)
                from app.models.resource import Resource
                resource = await Resource.find_one(Resource.telegram_message_id == message_id)
                
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

        # Register with Owner Filter
        # RESTRICTION: Only respond to owner ID configured in settings
        owner_id = settings.telegram_owner_id or 5422016608 # Fallback if not set
        owner_filter = filters.user(owner_id)
        
        self.client.add_handler(MessageHandler(start_handler, filters.command("start") & owner_filter))
        self.client.add_handler(MessageHandler(help_handler, filters.command("help") & owner_filter))
        self.client.add_handler(MessageHandler(search_handler, filters.command("search") & owner_filter))
        self.client.add_handler(MessageHandler(get_file_handler, filters.regex(r"^/get_\d+") & owner_filter))
    
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
            
            # Schedule backup upload (non-blocking)
            if self.backup_channel:
                asyncio.create_task(
                    self._backup_upload(file_bytes, filename, caption)
                )
            
            logger.info(f"File uploaded successfully: {filename} ({result['file_size']} bytes, file_id: {result['file_id']})")
            
            # Rate limiting: Wait after upload
            await asyncio.sleep(1)  # 1 second cooldown
            
            return result
            
        except FloodWait as e:
            logger.warning(f"FloodWait: sleeping for {e.value} seconds")
            await asyncio.sleep(e.value)
            return await self.upload_file(file_bytes, filename, caption, progress_callback)
        
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise Exception(f"Failed to upload to Telegram: {str(e)}")
    
    async def _backup_upload(
        self,
        file_bytes: bytes,
        filename: str,
        caption: str,
    ):
        """Upload file to backup channel (background task)."""
        try:
            file_stream = BytesIO(file_bytes)
            file_stream.name = filename
            
            await self.client.send_document(
                chat_id=self.backup_channel,
                document=file_stream,
                file_name=filename,
                caption=f"[BACKUP] {caption[:1000]}" if caption else "[BACKUP]",
                disable_notification=True,
            )
            logger.debug(f"Backup upload successful: {filename}")
            
        except Exception as e:
            logger.error(f"Backup upload failed: {e}")
    
    async def download_file(
        self,
        message_id: int,
        channel_id: Optional[int] = None,
        file_id: Optional[str] = None,  # For caching
    ) -> bytes:
        """Download a file from Telegram channel with caching."""
        if not await self.connect():
            raise Exception("Telegram client not connected - check credentials and network")
        
        channel_id = channel_id or self.primary_channel
        
        # Check cache first
        if file_id:
            cached = await cache_service.get_file(file_id, message_id)
            if cached:
                logger.info(f"Cache HIT for file {file_id}")
                return cached
        
        try:
            message = await self.client.get_messages(
                chat_id=channel_id,
                message_ids=message_id,
            )
            
            if not message or not message.document:
                raise Exception("Message or document not found")
            
            # Download to temp file then read
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                await self.client.download_media(
                    message=message,
                    file_name=tmp_path,
                )
                
                # Read the downloaded file
                with open(tmp_path, 'rb') as f:
                    file_bytes = f.read()
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            
            # Cache the result
            if file_id and file_bytes:
                await cache_service.set_file(
                    file_id,
                    message_id,
                    file_bytes,
                    ttl=3600,  # 1 hour
                )
                logger.info(f"Cached file {file_id} ({len(file_bytes)} bytes)")
            
            # Rate limiting: Wait after download
            await asyncio.sleep(1)  # 1 second cooldown
            
            return file_bytes
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise Exception(f"Failed to download from Telegram: {str(e)}")
    
    async def stream_file(
        self,
        message_id: int,
        channel_id: Optional[int] = None,
        chunk_size: int = 1024 * 1024,  # 1MB chunks
    ) -> AsyncIterator[bytes]:
        """Stream a file in chunks from Telegram channel."""
        if not await self.connect():
            raise Exception("Telegram client not connected")
        
        channel_id = channel_id or self.primary_channel
        
        try:
            message = await self.client.get_messages(
                chat_id=channel_id,
                message_ids=message_id,
            )
            
            if not message or not message.document:
                raise Exception("Message or document not found")
            
            async for chunk in self.client.stream_media(message, limit=chunk_size):
                yield chunk
                
        except Exception as e:
            logger.error(f"Stream failed: {e}")
            raise
    
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
