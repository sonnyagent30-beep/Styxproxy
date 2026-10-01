# QA audit — t_46761765: 19 "pre-existing" backend test failures

Branch `qa/t_46761765-failure-audit` @ `4980649d`. Baseline: `main` @ `f6c92110`.
No production code changed. Suite on main: **20 failed, 278 passed** (3 runs, stable).

The card's premise held up under checking: all failures are pre-existing, none
introduced by t_4007d162. But the "unrelated defect class" framing was too
generous. **One of them was a live security-coverage hole, and the rest were not
all defective tests.**

---

## 1. Classification of every failure

| # | Test(s) | Verdict | Root cause |
|---|---|---|---|
| 1 | `test_ops_auth.py` — 3 × `test_wrong_secret_returns_401` | **REAL DEFECT (test)** — security-critical | Tests a private copy of the auth logic. See §2. |
| 2 | `test_auth.py::TestRevokeTOTPSession` — 3 | Defective test | `monkeypatch.setattr(auth_module, "get_session", ...)` where `auth_module` is `app.routers.auth`. `app/routers/__init__.py` rebinds the name `auth` to the *router object*, so the module attribute is an `APIRouter`. Fix: `from app.routers import auth as auth_module` → importlib, or patch `app.routers.auth.get_session` by string. |
| 3 | `test_paystack_reference_join.py` — 6 | Defective test double | `FakeRequest` predates `resolve_origin()` (commit `8d2cb186`), which reads `request.client.host`. Fake has no `.client`/`.headers`. **Verified: adding both makes all 13 pass.** |
| 4 | `test_routers_orders.py::test_create_order_invalid_plan_code` | Defective test double + stale assertion | `MockSession.execute()` takes 1 arg; `resolve_plan` calls `execute(stmt, params)`. Also asserted `"Invalid plan code"` but production says `f"Invalid plan {plan_code} for country {country}"`. **Verified: both fixed → passes.** |
| 5 | `test_routers_payments.py::test_initiate_payment_requires_auth` | **Defective test — asserts a guarantee the product abandoned** | See §4. Endpoint has no `get_current_account` dependency; anonymous checkout is deliberate (commit `48d8b780`, "No signup required"). |
| 6 | `test_routers_payments.py::test_get_payment_status_requires_auth` | Defective test | Endpoint moved `/api/payments/{id}/status` → `/api/orders/{id}/status`. The old path 404s; the real path correctly returns **401**. The test is failing on a 404, not on a security gap. |
| 7 | `test_routers_webhooks.py::test_flutterwave_webhook_rejects_invalid_signature` | **Already fixed on main** | Fails only on the t_4007d162 branch, which is 3 commits behind main. `f6c92110` "never let rejection telemetry turn a 401 into a 500" fixes it. Not a live defect. |
| 8 | `test_routers_products.py` — 2 | Defective test **against a dead endpoint** | See §3. |
| 9 | `test_schemas.py::test_customer_phone_required` | Defective test, and it was **masking a real one** | See §4. |

**0 real production defects. 1 real test defect with security consequence. 8 defective tests.**

---

## 2. Lead finding: `test_ops_auth.py` asserts nothing

The whole file is a hand-copy. Lines 47–66 define `require_ops_role_test`, a
transcription of `app/services/ops_auth.py::require_ops_role`, and every test
calls `auth_result()` → that copy. The production module is imported by nothing
in the file.

**Proven, not inferred.** Replaced the production dependency with one that
authorises everyone, keeping a valid 401 path for nothing:

```
production require_ops_role -> def dep(request): return {"role": ..., "vulnerable": True}
15 passed
```

All 15 green with the real auth logic removed. The file's own docstring admits
it "test[s] the auth logic directly ... because the full FastAPI app has an
unrelated import error" — that import error is long fixed.

**Why the 3 failures in the card appeared and then vanished for me:** the file
reads `OPS_JWT_SECRET` at import with a fallback to `JWT_SECRET`
(test_ops_auth.py:28-30). When both env vars are equal, `_WRONG_SECRET` becomes
the *correct* secret, so `test_wrong_secret_returns_401` gets 200 and fails.
Reproduced exactly:

```
OPS_JWT_SECRET=shared-secret JWT_SECRET=shared-secret pytest tests/test_ops_auth.py
3 failed, 12 passed   <- the exact 3 from the card
```

So the pass/fail of a security test depended on the developer's shell. Anyone
running with matching secrets saw a red suite; everyone else saw green.

Fixed in `4980649d` with 11 tests against the real dependency. **Negative
control: all 9 mutations of ops-auth and phone behaviour turn the new file red.**

---

## 3. `KeyError: 'ISP-NG-1'` — the seed is fine, the endpoint is dead

Not missing seed data. `alembic/versions/005_add_plans.py:45-53` inserts exactly
the 7 plans the test expects, at exactly the prices it asserts. The test DB has
`plans` empty because `app/main.py:77` runs `Base.metadata.create_all`, which
creates tables but inserts no rows — and the DB was never migrated
(`alembic_version` does not exist).

The test passes only when CI happens to run `alembic upgrade head`, which is
`continue-on-error: true` in `.github/workflows/ci.yml:69`. So it depends on a
step the workflow is explicitly allowed to skip.

**But the endpoint is dead.** `/api/products` returns `[]` in production and
nothing calls it:

```
GET https://api.styxproxy.com/api/products  -> 200 {"products":[]}
plans in production: 1 row, is_active = false
GET https://api.styxproxy.com/api/catalog   -> 200, 21291 bytes   <- what the FE uses
```

`grep -rn "api/products" frontend/src backend/app` returns only the router's own
prefix. The storefront reads `/api/catalog` (21 KB, live) from
`country_plan_types` (33 enabled rows). These 2 tests pin prices for an endpoint
no customer reaches. **Low severity. Route as test deletion, not a fix** — and
delete the endpoint too, or the drift continues.

---

## 4. `customer_phone` — the test is wrong, but it was hiding QA-1

`test_customer_phone_required` is a **defective test**. `customer_phone` became
`Optional` in the same commit that made anonymous checkout work
(`48d8b780`); the router handles neither-phone-nor-email with a device-derived
identity. Requiring a phone would contradict shipped behaviour and break the
revenue path that commit was fixing.

The real finding is adjacent. **`PaymentInitiateRequest` is defined twice**:

- `app/schemas.py:572` — **dead copy**, missing `device_id`, `idempotency_key`, `quantity_gb`
- `app/routers/schemas.py:576` — **live**, imported by `app/routers/payments.py:22`

`tests/test_schemas.py` and `scripts/test_anonymous_checkout.py` import the
**dead** copy. So the one test that "looks like" it pins the payment request
contract was validating a shape the API does not accept. That is how a contract
test becomes decorative.

Second, subtler: `test_invalid_phone_raises` passes `"invalid"` (7 chars), which
`min_length=10` rejects **before** `validate_phone` runs. The format rule is
never exercised. Isolated by mutation — each rule survives removal alone:

```
A. drop min_length=10 only        -> SURVIVED (test still green)
B. neuter validate_phone only     -> SURVIVED (test still green)
C. both                          -> DETECTED
```

Two redundant rules, one assertion. Now pinned independently: a 10-char
non-phone (`"abcdefghij"`) must be rejected.

---

## 5. Suite-wide audit for the three scaffolding patterns

AST scan of all 27 test files, then mutation to confirm each finding:

| Pattern | Found | Status |
|---|---|---|
| P1 — test defines a copy of the production function | `test_ops_auth.py` (the 15-test hole) | **Fixed in `4980649d`** |
| P2 — `patch(ctor, return_value=X)` double-wraps | `test_credential_delivery_contract.py` × 6 | Already fixed on `fix/t_4007d162` |
| P3 — `raise_for_status` that cannot raise | `test_credential_delivery_contract.py` (mattered) · `test_paystack_reference_join.py` × 2 | First fixed on the same branch. The 2 paystack ones are happy-path only, so lower risk — **QA-6**, allowlisted with that reason. |
| P4 — test body with no assertion | 3 hits, all false positives (`assert_called_once` style, module-level `_load` helpers) | None |

P1/P2/P3 are now enforced by three meta-tests in the new file, each with an
explicit allowlist carrying a reason. Adding to an allowlist is a visible act.

---

## 6. What is genuinely well covered

Worth stating, because the headline is bad enough. Both webhook signature
mutations were caught by 5 tests each, including the t_604d405d contract suite:

- `verify_flutterwave_signature` → always-True: **caught** by 5 tests
- `verify_paystack_signature` → always-True: **caught**
- Flutterwave webhook → skip check: **caught** by 8 tests
- Paystack webhook → skip check: **caught**

**A webserver accepting an unsigned payment webhook is the worst bug this audit
could have found, and the suite would have caught it.** The hole is narrower than
the card feared: local ops auth, not payment webhooks.

Also confirmed not-a-defect: the 6 paystack failures are a stale fake, and the
"orders never rejects an unknown plan" mutation is caught **only once
`test_create_order_invalid_plan_code` is repaired** (proved by repairing it in a
scratch tree: mutation alone SURVIVES, repaired+mutation DETECTED). So that
failure is load-bearing — the defective test was masking real order-validation
coverage.

---

## 7. Mutations that survived — where coverage genuinely does not exist

Beyond ops-auth and the phone rules:

| Mutation | Caught by |
|---|---|
| `products`: `is_active` filter removed | **NOTHING** |
| `products`: `is_active` inverted (returns only inactive) | **NOTHING** |
| `products`: `country` filter removed | **NOTHING** |

All three are on the dead `/api/products` endpoint, so this is a consequence of
§3 rather than a separate risk — but it confirms no test in the tree can
distinguish a correct product query from a wrong one.

---

## 8. Recommended routing

| ID | Item | To | Severity |
|---|---|---|---|
| **QA-1** | Delete duplicate `PaymentInitiateRequest` from `app/schemas.py`; repoint `test_schemas.py` + `test_anonymous_checkout.py` at `app/routers/schemas.py`. 2 strict xfails flip on fix. | developer | **High** — a contract test validates a shape the API rejects |
| **QA-2** | Delete `tests/test_ops_auth.py`; replaced by 11 real tests in `4980649d`. | — done | **High** (security coverage) |
| **QA-3** | Delete `tests/test_routers_products.py` and `app/routers/products.py`; retire `/api/products`. Nothing calls it. | developer | Low |
| **QA-4** | Repair 4 test files: `test_auth.py` (import), `test_paystack_reference_join.py` (`FakeRequest.client`), `test_routers_orders.py` (`execute` arity + assertion), `test_routers_payments.py` (drop the 2 auth assertions — the guarantee no longer exists; keep a test that the *real* status route 401s). | developer | Medium |
| **QA-5** | `.github/workflows/ci.yml`: `alembic upgrade head` is `continue-on-error: true`, so every DB-dependent test is order-dependent on a step the workflow may skip. Also `continue-on-error: true` on the whole test job — **the suite cannot fail CI.** | devops | **High** |
| **QA-6** | `test_paystack_reference_join.py` `FakeResponse.raise_for_status` × 2 — make the fake able to fail before writing any gateway-failure test. | developer | Low |

**QA-5 is the finding that explains the other 19.** The test job is
`continue-on-error: true` (ci.yml:20), so a 20-failure suite has been green on
every PR. Nothing in this tree has been gating anything.
