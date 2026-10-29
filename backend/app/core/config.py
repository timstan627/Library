"""
Application Configuration
"""
from functools import lru_cache
from typing import Optional
from pydantic import Field
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
    debug: bool = False
    
    # Database (SQLite — file path managed in app/core/database.py)
    # database_url is no longer used; SQLite path is hardcoded in database.py
    database_url: str = "sqlite+aiosqlite:///student_library.db"
    
    # Security — secrets must come from the environment (or .env, which is
    # intentionally excluded from this repository).  Empty values are replaced
    # with a process-local random secret by SecurityManager, which is safe for
    # local development but invalidates tokens on restart.
    secret_key: str = ""
    jwt_secret_key: str = ""
    hmac_secret_key: str = ""
    access_token_expire_minutes: int = 60  # 1 hour
    refresh_token_expire_days: int = 30

    # Initial administrator bootstrap.  No credentials are embedded in code.
    initial_admin_email: Optional[str] = None
    initial_admin_password: Optional[str] = None

    # Trusted reverse-proxy addresses.  Forwarded client IP headers are only
    # honoured when the direct peer is one of these addresses.
    trusted_proxies: str = "127.0.0.1,::1"

    # Telegram — all credentials must be supplied via the environment.
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
    enable_rate_limiting: bool = True
    
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
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",") if ext.strip()]

    @property
    def trusted_proxies_list(self) -> list[str]:
        return [ip.strip() for ip in self.trusted_proxies.split(",") if ip.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
