"""Ops service JWT auth — verifies _ops/v1/ requests."""
import os
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request

_ops_jwt_secret = os.environ.get("OPS_JWT_SECRET")
if _ops_jwt_secret is None:
    raise ValueError(
        "OPS_JWT_SECRET environment variable is not set. "
        "Financial ops endpoints (/refund, /reprocess) require an explicit "
        "OPS_JWT_SECRET. Set it to a secure value: openssl rand -base64 32"
    )
OPS_JWT_SECRET: str = _ops_jwt_secret


def require_ops_role(RequiredRole: str = "ops-control"):
    """FastAPI dependency: verifies JWT has role == RequiredRole."""

    def dep(request: Request) -> dict:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(401, "Missing Bearer token")
        token = auth[7:]
        if not OPS_JWT_SECRET:
            raise HTTPException(401, "OPS_JWT_SECRET not configured")
        try:
            payload = jwt.decode(token, OPS_JWT_SECRET, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
        if payload.get("role") != RequiredRole:
            raise HTTPException(403, "Insufficient role")
        return payload  # returns JWT subject/info

    return dep


# Convenience dependency for ops-control role
ops_dep = Annotated[dict, Depends(require_ops_role("ops-control"))]
