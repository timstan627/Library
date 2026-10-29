"""
Security Middleware: headers, request timing, rate limiting.
"""
import time
from collections import defaultdict
from typing import Dict
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' http://localhost:* ws://localhost:*; "
            "frame-ancestors 'none'"
        )
        
        # HSTS (only meaningful over HTTPS, but set it for production readiness)
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Hide server info
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class AuthRateLimiter:
    """Track failed login attempts per IP+email AND per account.

    Two windows:
    - (ip, email): stops a single source hammering one account.
    - email only (larger budget): stops distributed/rotating-IP brute force
      against a single account, where every request looks like a new source.

    The account-wide budget is deliberately higher (shared NATs put many
    real users behind one IP/email pair).
    """

    ACCOUNT_WIDE_MULTIPLIER = 3

    def __init__(self, max_attempts: int = 5, lockout_minutes: int = 15):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_minutes * 60
        # Key: "ip:email" -> list of failed attempt timestamps
        self.failed_attempts: Dict[str, list] = defaultdict(list)
        # Key: email -> list of failed attempt timestamps (any IP)
        self.email_failures: Dict[str, list] = defaultdict(list)

    @staticmethod
    def _remaining(attempts: list, lockout_seconds: int) -> int:
        first = attempts[0]
        return max(1, int(lockout_seconds - (time.time() - first)))

    def check_and_record(self, ip: str, email: str) -> None:
        """Check if login is allowed; raise 429 if either window is locked."""
        key = f"{ip}:{email.lower()}"
        email_key = email.lower()
        now = time.time()

        # Keep only attempts inside the lockout window
        self.failed_attempts[key] = [
            t for t in self.failed_attempts[key] if now - t < self.lockout_seconds
        ]
        self.email_failures[email_key] = [
            t for t in self.email_failures[email_key] if now - t < self.lockout_seconds
        ]

        if len(self.failed_attempts[key]) >= self.max_attempts:
            remaining = self._remaining(self.failed_attempts[key], self.lockout_seconds)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Try again in {remaining // 60 + 1} minutes.",
                headers={"Retry-After": str(remaining)},
            )

        email_budget = self.max_attempts * self.ACCOUNT_WIDE_MULTIPLIER
        if len(self.email_failures[email_key]) >= email_budget:
            remaining = self._remaining(self.email_failures[email_key], self.lockout_seconds)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts for this account. Try again in {remaining // 60 + 1} minutes.",
                headers={"Retry-After": str(remaining)},
            )

    def record_failure(self, ip: str, email: str) -> None:
        """Record a failed login attempt in both windows."""
        self.failed_attempts[f"{ip}:{email.lower()}"].append(time.time())
        self.email_failures[email.lower()].append(time.time())

    def clear(self, ip: str, email: str) -> None:
        """Clear failed attempts on successful login."""
        self.failed_attempts.pop(f"{ip}:{email.lower()}", None)
        self.email_failures.pop(email.lower(), None)


# Global instance for auth rate limiting
auth_rate_limiter = AuthRateLimiter(max_attempts=5, lockout_minutes=15)


def get_client_ip(request: Request) -> str:
    """Rate-limit identity: the direct peer address.

    X-Forwarded-For / X-Real-IP are client-controlled headers — trusting them
    blindly would let anyone spoof a fresh rate-limit bucket (or get a victim
    IP locked out). They are honoured only when the request arrives from a
    trusted reverse proxy (settings.trusted_proxies), e.g. nginx on loopback.
    """
    client_host = request.client.host if request.client else "unknown"
    if client_host in settings.trusted_proxies_list:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            first_hop = forwarded.split(",")[0].strip()
            if first_hop:
                return first_hop
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
    return client_host


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    For production, use Redis-based rate limiting.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Get client IP (trusted-proxy aware)
        client_ip = get_client_ip(request)
        
        # Clean old requests
        current_time = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < 60
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            # Must return a response directly: exceptions raised inside
            # BaseHTTPMiddleware bypass FastAPI's exception handlers and
            # surface to the client as a 500 instead of a 429.
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": "60"},
            )
        
        # Record request
        self.requests[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.requests[client_ip])
        )
        
        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Add request timing header."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        return response
