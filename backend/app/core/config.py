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
    app_url: str = "http://localhost:3000"
    environment: str = "development"
    debug: bool = True
    
    # Database (MongoDB)
    database_url: str = "mongodb://localhost:27017/student_library"
    
    # Security
    secret_key: str = "change-this-in-production"
    jwt_secret_key: str = "change-this-jwt-secret"
    hmac_secret_key: str = "change-this-hmac-secret"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    
    # Telegram
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_primary_channel: Optional[int] = None
    telegram_backup_channel: Optional[int] = None
    telegram_owner_id: Optional[int] = None
    
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
    enable_rate_limiting: bool = False
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
