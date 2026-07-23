# Styxproxy — API Contract (D1)

**Generated:** 2026-07-23
**Purpose:** Single source of truth for FE ↔ BE field naming, types, and validation.

## Convention

- All requests use **snake_case** field names (Python/FastAPI default).
- All responses use **snake_case** from BE; FE types mirror 1:1.
- IDs are UUIDs (string in JSON).
- Timestamps are ISO 8601 UTC strings.
- All money is in **kobo** (1 NGN = 100 kobo) — never floats.

## Single source of truth

**Backend:** `backend/app/schemas.py` (Pydantic models) — authoritative.
**Frontend mirror:** `frontend/src/types/index.ts` — must stay in sync.

A field exists in FE types only if it's used by a UI component.
A field exists in BE schemas only if it's accepted/returned by an endpoint.

## Validation rules (applied at BE)

| Field type | Validation | Error code |
|---|---|---|
| `email` | regex `^[^@]+@[^@]+\.[^@]+$` | 422 |
| `password` | min_length=1 (any non-empty) | 422 |
| `totp_code` | min_length=6, max_length=6, digits only | 422 |
| `pin` | min_length=4, max_length=6, digits only | 422 |
| `admin_phone` | min_length=10, max_length=20 (E.164-ish) | 422 |
| `slug` | min_length=1, max_length=200, lowercase | 422 |
| `country` | min_length=2, max_length=10, uppercase ISO | 422 |
| `plan_code` | min_length=1, max_length=50 | 422 |
| `message` (free text) | max_length=1000 | 422 |
| `reason` | max_length=500 | 422 |

## Error response format (consistent across all endpoints)

```json
{
  "detail": "Human-readable error message"
}
```

Or for Pydantic 422:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters",
      "input": "..."
    }
  ]
}
```

## HTTP status codes

| Code | Meaning in Styxproxy |
|---|---|
| 200 | OK |
| 201 | Resource created |
| 204 | Deleted / no content |
| 400 | Bad input (logical, not schema) |
| 401 | Not authenticated (admin token missing/invalid) |
| 403 | Authenticated but not allowed (role check) |
| 404 | Resource not found |
| 409 | Conflict (duplicate, state) |
| 422 | Pydantic validation failed |
| 429 | Rate limited |
| 500 | Server error |
| 503 | Maintenance mode active (public routes) |

## Auth header

`Authorization: Bearer <jwt>` for all `/api/admin/*` and `/api/auth/*`.
No header needed for `/api/public/*`, `/api/health`, `/api/products`, `/api/blog`.

## Rate limits

| Endpoint group | Limit |
|---|---|
| Public reads | 60 req/min per IP |
| Auth endpoints | 6 attempts/min per IP |
| Webhooks | 100 req/min per IP |
| Admin reads | 300 req/min per admin |

## ID generation

- All new records get `uuid.uuid4()` as the primary key.
- Customer phone is stored as a one-way hash (not the raw phone).
- Admin email is the natural key (unique) — used in URLs.

## Money handling

- BE stores: integer kobo (`amount_kobo`).
- Flutterwave API: amount in lowest denomination (already kobo).
- FE displays: kobo ÷ 100, formatted as `₦6,500.00`.

## Pagination

All list endpoints use `page` (1-indexed) + `page_size` (default 20, max 100).

Response shape:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 153,
    "has_next": true
  }
}
```

## How to add a new endpoint

1. Add the Pydantic request + response models to `backend/app/schemas.py` with validators.
2. Add the route to the appropriate router in `backend/app/routers/`.
3. Add the corresponding TypeScript type to `frontend/src/types/index.ts`.
4. Add the `api.<method>()` call to `frontend/src/lib/api.ts`.
5. Update this doc with the new endpoint (one row in the relevant section).

## Drift detection

- Manual: PR reviewer checks that all `this.request()` calls in FE have a matching route in BE.
- Automated: TODO — generate an OpenAPI spec from FastAPI and diff against FE types.

## Audit trail (D1 cross-ref)

- This file is the single source of truth for the contract.
- Pydantic schemas are auto-validated by FastAPI on every request — invalid input NEVER reaches the DB.
- All SQL queries use SQLAlchemy ORM or parameterized `text()` calls — no string concatenation with user input.
