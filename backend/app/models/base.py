"""
Base Model Mixins (MongoDB)
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import Field, BaseModel

class TimestampMixin(BaseModel):
    """Mixin for created_at and updated_at timestamps."""
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        # Beanie settings if needed
        pass
    
    async def save(self, *args, **kwargs):
        """Update updated_at timestamp on save."""
        self.updated_at = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)
