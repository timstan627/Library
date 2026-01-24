"""
Authentication API Routes
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.core.config import settings
from app.core.security import security_manager
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
):
    """Register a new user."""
    # Check if email already exists
    if await User.find_one(User.email == user_data.email.lower()):
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
    
    await user.create()
    
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    request: Request,
):
    """Login with email and password."""
    # Find user
    user = await User.find_one(User.email == login_data.email.lower())
    
    if not user or not security_manager.verify_password(
        login_data.password, user.password_hash
    ):
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
    
    # Check if MFA is required
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
        user=user,
        refresh_token_hash=security_manager.hash_api_key(tokens["refresh_token"]),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    await session.create()
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await user.save()
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: dict,
):
    """Refresh access token using refresh token."""
    refresh_token = request.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token is required",
        )
    payload = security_manager.verify_token(refresh_token, token_type="refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user_id = payload.get("sub")
    
    # Verify session exists and is not revoked
    token_hash = security_manager.hash_api_key(refresh_token)
    
    session = await Session.find_one(
        Session.refresh_token_hash == token_hash,
        Session.is_revoked == False,
        Session.expires_at > datetime.now(timezone.utc),
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or expired",
        )
    
    # Generate new tokens
    tokens = security_manager.create_tokens(user_id)
    
    # Update session with new refresh token
    session.refresh_token_hash = security_manager.hash_api_key(tokens["refresh_token"])
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    
    await session.save()
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
):
    """Logout and revoke current session."""
    # Revoke all sessions for this user
    # In Beanie we deal with Links differently, querying sessions by user ID needs care if user is a link.
    # But Session.user is a Link.
    
    sessions = await Session.find(
        Session.user.id == current_user.id, 
        Session.is_revoked == False
    ).to_list()
    
    for session in sessions:
        session.is_revoked = True
        await session.save()
    
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
):
    """Setup MFA for the current user."""
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )
    
    # Generate MFA secret
    secret = security_manager.generate_mfa_secret()
    
    # Store secret (not yet enabled)
    current_user.mfa_secret = secret
    await current_user.save()
    
    # Generate QR code
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
    await current_user.save()
    
    return {"message": "MFA enabled successfully"}


@router.post("/disable-mfa")
async def disable_mfa(
    data: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
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
    await current_user.save()
    
    return {"message": "MFA disabled successfully"}
