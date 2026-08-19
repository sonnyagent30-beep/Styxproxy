# SECURITY NOTE — t_b5831cf4
**Review date:** 2026-08-19
**Reviewer:** security-auditor
**File reviewed:** `backend/app/routers/ops.py` + `backend/app/services/ops_auth.py`

---

## 1. Auth status of each `/_ops/v1/` endpoint

| Endpoint | Auth applied? | Dependency |
|---|---|---|
| `/_ops/v1/health` | ✅ YES | `Depends(require_ops_role("ops-control"))` |
| `/_ops/v1/metrics` | ✅ YES | `Depends(require_ops_role("ops-control"))` |
| `/_ops/v1/health/history` | ✅ YES | `Depends(require_ops_role("ops-control"))` |
| `/_ops/v1/orders/{id}/refund` | ✅ YES | `Depends(require_ops_role("ops-control"))` |
| `/_ops/v1/orders/{id}/reprocess` | ✅ YES | `Depends(require_ops_role("ops-control"))` |
| `/_ops/v1/slow-queries` | ✅ YES | `Depends(require_ops_role("ops-control"))` |

**Finding:** All six endpoints currently have `require_ops_role("ops-control")` applied.
The task description's claim of unauthenticated exposure is **not confirmed** — no
endpoint in the current codebase is missing auth. However, the docstring on
`ops_health_history` (line 371) reads *"no admin auth required"* which is
incorrect and should be corrected to avoid future confusion.

---

## 2. Sensitive data exposed by `/_ops/v1/metrics` (when auth is satisfied)

| Field | Sensitivity |
|---|---|
| `total_customers` | Medium — reveals platform scale |
| `total_orders`, `paid_count`, `fulfilled_count`, `refunded_count` | Medium — reveals business volume |
| `revenue_ngn` | **HIGH** — direct revenue exposure in NGN |
| `trial_count` | Low — trial usage metric |
| `active_credentials` | Medium — reveals active subscription count |

The `/health` and `/health/history` endpoints expose infrastructure topology
(DB connectivity status, Redis status, LiteLLM/Ollama/M2 cloud connectivity,
latency metrics) which is Medium sensitivity (infrastructure enumeration).

---

## 3. Required JWT claim for `require_ops_role`

**Current implementation** (`ops_auth.py` line 32):
```python
if payload.get("role") != RequiredRole:
    raise HTTPException(403, "Insufficient role")
```

`require_ops_role` checks for an **exact string match** on the top-level JWT
claim `role`. The expected JWT payload must contain:

```json
{ "role": "ops-control", ... }
```

No `scopes` array, no nested claims — a plain `role: "ops-control"` string at
the payload root.

---

## 4. Recommended dependency design

All three read endpoints share the `/_ops/v1/` prefix and require identical
auth. The most maintainable pattern is a **router-level dependency**:

### Recommended `ops_auth.py` signature

```python
from fastapi import HTTPException, Request
import jwt

OPS_JWT_SECRET: str  # raised ValueError at import if env missing

def require_ops_role(required_role: str = "ops-control") -> dict:
    """FastAPI dependency. Returns the decoded JWT payload on success."""
    def dep(request: Request) -> dict:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized", "message": "Missing Bearer token"}
            )
        try:
            payload = jwt.decode(
                auth[7:], OPS_JWT_SECRET, algorithms=["HS256"]
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized", "message": "Invalid token"}
            )
        if payload.get("role") != required_role:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "message": f"Role '{required_role}' required"
                }
            )
        return payload
    return dep
```

### Usage — router-level (recommended for shared prefix)

```python
from app.services.ops_auth import require_ops_role

router = APIRouter(prefix="/_ops/v1", tags=["ops"],
                   dependencies=[Depends(require_ops_role("ops-control"))])
```

The router-level `dependencies=[Depends(...)]` applies auth to every route in
the router without repetition. Per-endpoint `Depends()` on individual routes is
still valid and takes priority — useful for any route that needs a different
role.

### Error response shape

All auth failures return the same structure for consistent client handling:

```json
{
  "error": "unauthorized" | "forbidden",
  "message": "Human-readable reason"
}
```

| Scenario | HTTP Status | `error` value |
|---|---|---|
| Missing `Authorization` header | 401 | `unauthorized` |
| Malformed / expired / bad-signature token | 401 | `unauthorized` |
| `role` claim mismatch | 403 | `forbidden` |

---

## 5. Actions

1. **[DONE — confirm auth present]** No endpoint is currently unprotected.
2. **[FIX docstring]** `ops_health_history` docstring line 371 currently says
   *"no admin auth required"* — change to *"requires role: ops-control"*.
3. **[CONSIDER router-level]** Migrate to router-level `dependencies=[Depends(
   require_ops_role("ops-control"))]` to guarantee any new `/_ops/v1/` route
   inherits auth automatically and cannot be added without it.
4. **[OPS_JWT_SECRET rotation]** Confirm `OPS_JWT_SECRET` is rotated out-of-band
   and stored in a secrets manager, not committed to source control.
