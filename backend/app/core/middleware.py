import time
import uuid
import json
import logging
from typing import Dict, List, Any
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("AppMiddleware")

# Simple in-memory rate limiter per IP for auth & discover endpoints (60 req/min)
RATE_LIMIT_STORE: Dict[str, List[float]] = {}
RATE_LIMIT_WINDOW = 60 # seconds
MAX_REQUESTS_PER_WINDOW = 60

PII_KEYS = {"email", "annual_income", "income", "social_category", "disability", "minority", "bpl_card", "password"}

def redact_pii(data: Any) -> Any:
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if k in PII_KEYS:
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_pii(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_pii(i) for i in data]
    return data

class HardeningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = str(uuid.uuid4())
        request.state.request_id = req_id
        t0 = time.time()

        # 1. Rate Limiting for Auth & Discovery endpoints
        path = request.url.path
        if path.startswith("/auth") or path.startswith("/discover"):
            client_ip = request.client.host if request.client else "127.0.0.1"
            now = time.time()
            timestamps = RATE_LIMIT_STORE.get(client_ip, [])
            valid_timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
            if len(valid_timestamps) >= MAX_REQUESTS_PER_WINDOW:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded. Please try again later."}
                )
            valid_timestamps.append(now)
            RATE_LIMIT_STORE[client_ip] = valid_timestamps

        # 2. Process Request
        response = await call_next(request)

        # 3. Security Headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["X-Request-ID"] = req_id

        # 4. Structured JSON Logging with PII Redaction
        latency_ms = int((time.time() - t0) * 1000)
        log_data = {
            "request_id": req_id,
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "query_params": redact_pii(dict(request.query_params))
        }
        logger.info(json.dumps(log_data))

        return response
