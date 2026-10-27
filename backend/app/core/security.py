"""
Security Utilities - Authentication, Hashing, JWT, MFA
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from jose import jwt, JWTError
from passlib.context import CryptContext
import pyotp
import qrcode
import qrcode.image.svg
from qrcode.image.pure import PyPNGImage
from io import BytesIO
import base64

from app.core.config import settings


# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


class SecurityManager:
    """Centralized security utilities."""
    
    def __init__(self):
        self.algorithm = "HS256"
        self.access_token_expire = settings.access_token_expire_minutes
        self.refresh_token_expire = settings.refresh_token_expire_days
    
    # ==================== Password Hashing ====================
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    # ==================== JWT Tokens ====================
    
    def create_access_token(
        self,
        data: dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.access_token_expire
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
        })
        
        return jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=self.algorithm,
        )
    
    def create_refresh_token(
        self,
        data: dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=self.refresh_token_expire
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
            "jti": secrets.token_urlsafe(16),  # Token ID for revocation
        })
        
        return jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=self.algorithm,
        )
    
    def create_tokens(self, user_id: str) -> dict[str, str]:
        """Generate access + refresh token pair."""
        access_token = self.create_access_token({"sub": user_id})
        refresh_token = self.create_refresh_token({"sub": user_id})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[dict]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[self.algorithm],
            )
            
            if payload.get("type") != token_type:
                return None
            
            return payload
        except JWTError:
            return None
    
    # ==================== MFA (TOTP) ====================
    
    def generate_mfa_secret(self) -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    def get_mfa_provisioning_uri(
        self,
        secret: str,
        email: str,
        issuer: str = "Student Library",
    ) -> str:
        """Get the provisioning URI for authenticator apps."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)
    
    def generate_mfa_qr_code(
        self,
        secret: str,
        email: str,
        issuer: str = "Student Library",
    ) -> str:
        """Generate a QR code for MFA setup as base64 PNG."""
        uri = self.get_mfa_provisioning_uri(secret, email, issuer)

        # Explicit pure-Python PNG factory: PIL is not installed, and the
        # default PyPNG backend's save() rejects PIL-style kwargs.
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
            image_factory=PyPNGImage,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode()
    
    def verify_mfa_code(self, secret: str, code: str) -> bool:
        """Verify a TOTP code."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    
    # ==================== API Keys ====================
    
    def generate_api_key(self) -> tuple[str, str]:
        """Generate a new API key. Returns (key, hash)."""
        key = f"slk_{secrets.token_urlsafe(32)}"
        key_hash = self.hash_api_key(key)
        return key, key_hash
    
    def hash_api_key(self, key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def verify_api_key(self, key: str, key_hash: str) -> bool:
        """Verify an API key against its hash."""
        return hmac.compare_digest(
            self.hash_api_key(key),
            key_hash,
        )
    
    # ==================== File Hashing ====================
    
    def hash_file(self, file_bytes: bytes) -> str:
        """Generate SHA-256 hash of file content."""
        return hashlib.sha256(file_bytes).hexdigest()
    
    def hash_file_streaming(self, file_path: str) -> str:
        """Generate SHA-256 hash of a file by streaming."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    # ==================== HMAC Request Signing ====================
    
    def generate_hmac_signature(
        self,
        timestamp: str,
        body: str,
    ) -> str:
        """Generate HMAC signature for request verification."""
        message = f"{timestamp}:{body}"
        return hmac.new(
            settings.hmac_secret_key.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
    
    def verify_hmac_signature(
        self,
        signature: str,
        timestamp: str,
        body: str,
        max_age_seconds: int = 300,
    ) -> bool:
        """Verify HMAC signature with replay attack prevention."""
        # Check timestamp age
        try:
            request_time = int(timestamp)
            current_time = int(datetime.now(timezone.utc).timestamp())
            
            if abs(current_time - request_time) > max_age_seconds:
                return False
        except (ValueError, TypeError):
            return False
        
        # Verify signature
        expected = self.generate_hmac_signature(timestamp, body)
        return hmac.compare_digest(signature, expected)
    
    # ==================== Utilities ====================
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(length)
    
    def generate_email_verification_token(self) -> str:
        """Generate a token for email verification."""
        return secrets.token_urlsafe(48)
    
    def generate_password_reset_token(self) -> str:
        """Generate a token for password reset."""
        return secrets.token_urlsafe(48)


# Global instance
security_manager = SecurityManager()
