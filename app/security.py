import hmac
import hashlib
import time
import html
import re
from typing import Dict, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from app.config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, WHATSAPP_APP_SECRET

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Hardens HTTP response headers to protect against common web attacks:
    - XSS (Cross Site Scripting)
    - Clickjacking (X-Frame-Options)
    - MIME sniffing (X-Content-Type-Options)
    - Information leakage
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        # Content Security Policy allows self, cdnjs, fonts, and inline styles for dynamic rendering
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com data: blob:; "
            "img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com;"
        )
        return response


class RateLimiter:
    """
    In-memory Sliding Window Rate Limiter.
    Protects against denial-of-service (DoS) and brute force attacks.
    Zero external dependency (no Redis needed, zero server cost).
    """
    def __init__(self, max_requests: int = RATE_LIMIT_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: Dict[str, list] = {}

    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Clean expired timestamps
        history = self.clients.get(client_ip, [])
        history = [ts for ts in history if ts > cutoff]
        
        if len(history) >= self.max_requests:
            remaining = 0
            self.clients[client_ip] = history
            return False, remaining
        
        history.append(now)
        self.clients[client_ip] = history
        remaining = self.max_requests - len(history)
        return True, remaining


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude static assets from strict rate limits
        path = request.url.path
        if path.startswith("/static") or path == "/favicon.ico":
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        allowed, remaining = rate_limiter.is_allowed(client_ip)
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": "Rate limit exceeded. Please wait a few moments before trying again.",
                    "security_note": "Automated security filter active."
                },
                headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
            )
            
        response: Response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


def sanitize_input(value: str) -> str:
    """
    Sanitizes user input string against HTML injection and XSS payloads.
    """
    if not isinstance(value, str):
        return value
    # Strip script tags, event handlers, and javascript: protocols
    cleaned = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", value, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"on\w+\s*=", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"javascript:\s*", "", cleaned, flags=re.IGNORECASE)
    # HTML escape remaining content for safe display
    return html.escape(cleaned.strip())


def verify_whatsapp_signature(body: bytes, signature_header: str) -> bool:
    """
    Verifies that the incoming webhook payload genuinely originated from Meta/WhatsApp Cloud API
    using SHA-256 HMAC signature. Prevents forged orders and attacker injection.
    """
    if not WHATSAPP_APP_SECRET:
        # In local/testing mode where secret isn't configured, permit local simulator
        return True
    
    if not signature_header or not signature_header.startswith("sha256="):
        return False
        
    expected_hash = signature_header.split("sha256=")[-1]
    computed_hmac = hmac.new(
        WHATSAPP_APP_SECRET.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_hash, computed_hmac)
