"""
Audit Trail Middleware — automatically records every mutating API call
(POST, PUT, PATCH, DELETE) into the audit_trails table.

The middleware is non-blocking: it fires the DB write in a background task
so it never adds latency to the main request.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Only audit mutating methods
_AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Skip paths that are noisy / internal
_SKIP_PREFIXES = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi",
    "/favicon",
}


class AuditTrailMiddleware(BaseHTTPMiddleware):
    """
    Intercepts every HTTP request and, after the response is sent,
    creates an AuditTrail record for mutating operations.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if request.method not in _AUDIT_METHODS:
            return response

        path = request.url.path
        if any(path.startswith(skip) for skip in _SKIP_PREFIXES):
            return response

        # Resolve user from token without blocking the response
        asyncio.create_task(
            self._write_audit(request, response.status_code)
        )
        return response

    async def _write_audit(self, request: Request, status_code: int) -> None:
        try:
            from app.models.iam import AuditTrail

            # Try to extract user_id from JWT without raising
            user_id: int | None = None
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                try:
                    from app.core.security import decode_token
                    payload = decode_token(token)
                    user_id = int(payload.get("sub", 0)) or None
                except Exception:
                    pass

            # Build details dict
            details = {
                "status_code": status_code,
                "query_params": str(request.query_params) or None,
                "request_id": getattr(request.state, "request_id", None),
            }

            # Extract resource type & id from path
            # e.g. /api/v1/vessels/42 → resource_type="vessels", resource_id=42
            resource_type: str | None = None
            resource_id: int | None = None
            parts = [p for p in request.url.path.split("/") if p]
            for i, part in enumerate(parts):
                if part not in ("api", "v1", "ops", "ai", "opt", "analytics", "auth",
                                "privacy", "import", "export", "work-orders", "visits") \
                        and not part.isdigit():
                    resource_type = part
                    if i + 1 < len(parts) and parts[i + 1].isdigit():
                        resource_id = int(parts[i + 1])
                    break

            async with AsyncSessionLocal() as db:
                audit = AuditTrail(
                    user_id=user_id,
                    action=f"{request.method}:{request.url.path}",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=self._get_client_ip(request),
                    user_agent=request.headers.get("user-agent", "")[:500],
                    details=json.dumps(details),
                    occurred_at=datetime.now(timezone.utc),
                )
                db.add(audit)
                await db.commit()
        except Exception as exc:
            # Audit failures must NEVER affect the user experience
            logger.debug("Audit write failed (non-critical): %s", exc)

    @staticmethod
    def _get_client_ip(request: Request) -> str | None:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return None
