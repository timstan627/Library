"""
Authentication API Routes (SQLAlchemy)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import security_manager
from app.core.middleware import auth_rate_limiter
from app.core.database import get_db
from app.models.user import User, Session
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    MFASetupResponse,
    MFAVerifyRequest,
)
from app.api.v1.deps import get_current_user, get_current_active_user

router = APIRouter(redirect_slashes=False)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create user
    user = User(
        email=user_data.email.lower(),
        password_hash=security_manager.hash_password(user_data.password),
        display_name=user_data.display_name,
        storage_quota_bytes=settings.storage_quota_bytes,
    )
    
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    # Invalidate cached stats
    from app.services.cache import cache_service
    cache_service.invalidate_on_user_change()
    
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password."""
    # Brute force protection
    client_ip = request.client.host if request.client else "unknown"
    auth_rate_limiter.check_and_record(client_ip, login_data.email)
    
    # Find user
    result = await db.execute(select(User).where(User.email == login_data.email.lower()))
    user = result.scalar_one_or_none()
    
    if not user or not security_manager.verify_password(
        login_data.password, user.password_hash
    ):
        auth_rate_limiter.record_failure(client_ip, login_data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account banned: {user.ban_reason or 'No reason provided'}",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )
    
    # Check MFA
    if user.mfa_enabled:
        if not login_data.mfa_code:
            return TokenResponse(
                access_token="",
                refresh_token="",
                requires_mfa=True,
            )
        
        if not security_manager.verify_mfa_code(user.mfa_secret, login_data.mfa_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code",
            )
    
    # Create tokens
    tokens = security_manager.create_tokens(str(user.id))
    
    # Create session
    session = Session(
        user_id=user.id,
        refresh_token_hash=security_manager.hash_api_key(tokens["refresh_token"]),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    
    await db.flush()
    
    # Clear failed attempts
    auth_rate_limiter.clear(client_ip, login_data.email)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: dict,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    refresh_tok = request.get("refresh_token")
    if not refresh_tok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token is required",
        )
    payload = security_manager.verify_token(refresh_tok, token_type="refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user_id = payload.get("sub")
    
    # Verify session exists
    token_hash = security_manager.hash_api_key(refresh_tok)
    
    result = await db.execute(
        select(Session).where(
            Session.refresh_token_hash == token_hash,
            Session.is_revoked == False,
            Session.expires_at > datetime.now(timezone.utc),
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or expired",
        )
    
    # Generate new tokens
    tokens = security_manager.create_tokens(user_id)
    
    # Update session
    session.refresh_token_hash = security_manager.hash_api_key(tokens["refresh_token"])
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    
    await db.flush()
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout and revoke current session."""
    result = await db.execute(
        select(Session).where(
            Session.user_id == current_user.id,
            Session.is_revoked == False,
        )
    )
    sessions = result.scalars().all()
    
    for session in sessions:
        session.is_revoked = True
    
    await db.flush()
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user profile."""
    return current_user


@router.post("/setup-mfa", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Setup MFA for the current user."""
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )
    
    secret = security_manager.generate_mfa_secret()
    current_user.mfa_secret = secret
    
    await db.flush()
    
    qr_code = security_manager.generate_mfa_qr_code(
        secret, current_user.email, settings.app_name
    )
    uri = security_manager.get_mfa_provisioning_uri(
        secret, current_user.email, settings.app_name
    )
    
    return MFASetupResponse(
        secret=secret,
        qr_code_base64=qr_code,
        provisioning_uri=uri,
    )


@router.post("/verify-mfa")
async def verify_mfa(
    data: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify and enable MFA."""
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated",
        )
    
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )
    
    if not security_manager.verify_mfa_code(current_user.mfa_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )
    
    current_user.mfa_enabled = True
    await db.flush()
    
    return {"message": "MFA enabled successfully"}


@router.post("/disable-mfa")
async def disable_mfa(
    data: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable MFA."""
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )
    
    if not security_manager.verify_mfa_code(current_user.mfa_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )
    
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    await db.flush()
    
    return {"message": "MFA disabled successfully"}
