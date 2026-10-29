"""
Password Reset API endpoint (SQLAlchemy)

Token store: in-memory, holding only SHA-256 digests (a memory read can't be
replayed as a valid reset link — the raw token exists solely in the email
delivered to the account owner).

Invariants enforced here:
- Exactly ONE live token per account (a new request invalidates the old link).
- Single-use via atomic pop: two concurrent confirms with the same token
  cannot both succeed.
- Issuance is throttled per account (email-bombing guard) on top of the
  global per-IP middleware limit.
- Confirm re-checks is_active (issuance checks it too; state can change
  between the two).
- Every completed reset is written to the audit log.
"""
import hashlib
import secrets
import time
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import security_manager
from app.models.user import User, Session
from app.models.audit_log import AuditLog
from app.schemas.user import PasswordResetRequest, PasswordResetConfirm

logger = logging.getLogger(__name__)

router = APIRouter()

password_reset_tokens: dict[str, tuple[str, datetime]] = {}

# Per-account issuance throttle: (email -> [request timestamps])
_EMAIL_REQUEST_WINDOW = 3600  # 1 hour
_EMAIL_REQUEST_LIMIT = 3
_email_requests: dict[str, list] = defaultdict(list)

# Hard cap for the token store (defense in depth; the sweep plus
# one-token-per-user normally keep it far below this)
_MAX_TOKENS = 10_000


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _sweep_tokens(now: datetime) -> None:
    """Drop expired entries; called opportunistically to bound the store."""
    expired = [h for h, (_, exp) in password_reset_tokens.items() if now > exp]
    for h in expired:
        password_reset_tokens.pop(h, None)


def _issue_throttled(email: str) -> None:
    """Raise 429 when this account asked for too many reset emails."""
    now = time.time()
    attempts = [t for t in _email_requests[email] if now - t < _EMAIL_REQUEST_WINDOW]
    _email_requests[email] = attempts
    if len(attempts) >= _EMAIL_REQUEST_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many reset requests for this account. Try again later.",
            headers={"Retry-After": str(_EMAIL_REQUEST_WINDOW)},
        )
    attempts.append(now)


@router.post("/forgot-password")
async def forgot_password(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Request password reset email.

    The response is identical whether or not the account exists (no
    account enumeration).
    """
    _issue_throttled(data.email.lower())
    now = datetime.now(timezone.utc)
    _sweep_tokens(now)

    result = await db.execute(select(User).where(User.email == data.email.lower()))
    user = result.scalar_one_or_none()

    if user and user.is_active and not user.is_banned:
        # One live link per account: any previous token is void the moment
        # a new one is issued.
        for h in [h for h, (uid, _) in password_reset_tokens.items() if uid == str(user.id)]:
            password_reset_tokens.pop(h, None)

        if len(password_reset_tokens) < _MAX_TOKENS:
            token = secrets.token_urlsafe(32)
            expires_at = now + timedelta(hours=1)
            password_reset_tokens[_hash_token(token)] = (str(user.id), expires_at)

            from app.services.email import email_service
            background_tasks.add_task(email_service.send_reset_password_email, user.email, token)
        else:
            # Store full — refuse to issue rather than send a dead link.
            logger.error("Password-reset token store full; not issuing token")

    return {"message": "If an account exists, a reset link will be sent."}


@router.post("/reset-password")
async def reset_password(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using token."""
    # Atomic single-use: pop the entry — a concurrent confirm with the same
    # token gets None and fails instead of both succeeding.
    entry = password_reset_tokens.pop(_hash_token(data.token), None)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user_id, expires_at = entry
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or user.is_banned or not user.is_active:
        # Banned/deactivated accounts can't complete a reset to regain access
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user.password_hash = security_manager.hash_password(data.new_password)

    # New password invalidates every existing session
    await db.execute(delete(Session).where(Session.user_id == user.id))

    # Audit: who reset (the account owner via token), when, from where
    db.add(
        AuditLog(
            action="reset_password",
            actor_id=user.id,
            target_type="user",
            target_id=user.id,
        )
    )
    await db.flush()

    return {"message": "Password reset successfully"}
