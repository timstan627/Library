"""
Application Configuration
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "Student Resource Library"
    app_url: str = "http://127.0.0.1:3000"
    environment: str = "development"
    debug: bool = True
    
    # Database (SQLite — file path managed in app/core/database.py)
    # database_url is no longer used; SQLite path is hardcoded in database.py
    database_url: str = "sqlite+aiosqlite:///student_library.db"
    
    # Cache is in-memory (app/services/cache.py) — no external services needed
    
    # Security
    secret_key: str = "change-this-in-production"
    jwt_secret_key: str = "change-this-jwt-secret"
    hmac_secret_key: str = "change-this-hmac-secret"
    access_token_expire_minutes: int = 1440  # 24 hours
    refresh_token_expire_days: int = 30
    
    # Telegram
    telegram_api_id: Optional[int] = 16501053
    telegram_api_hash: Optional[str] = "d8c9b01c863dabacc484c2c06cdd0f6e"
    telegram_bot_token: Optional[str] = "8385481456:AAFk2g6SPQGmCN-1lXFZjspV8ZLhh1MpoF0"
    telegram_primary_channel: Optional[int] = -1002284190309
    telegram_backup_channel: Optional[int] = -1002284190309
    telegram_owner_id: Optional[int] = 5422016608
    
    # Email (SMTP)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    emails_from_email: Optional[str] = None
    emails_from_name: str = "Student Library"
    
    # File Upload
    max_file_size_mb: int = 50
    storage_quota_mb: int = 104_857_600 # 100TB (Unlimited)
    allowed_extensions: str = "pdf,docx,pptx,xlsx,zip,txt,md,jpg,png"
    
    # Features
    enable_mfa: bool = True
    enable_rate_limiting: bool = True
    enable_sentry: bool = False
    sentry_dsn: Optional[str] = None
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def storage_quota_bytes(self) -> int:
        return self.storage_quota_mb * 1024 * 1024
    
    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
