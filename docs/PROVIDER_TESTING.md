# Provider Testing & Benchmark Tiers

**Purpose:** Define how Styxproxy tests and classifies proxy providers before onboarding and during ongoing operation.

**Test script:** `backend/app/services/provider_test.py`

---

## Benchmark Tiers

Providers are classified into four tiers based on their test scores:

| Tier | Score | Meaning | Action |
|------|-------|---------|--------|
| **A — Preferred** | 85–100 | Excellent IP quality, reliable delivery, strong support | Use for all plan types |
| **B — Approved** | 70–84 | Good quality, minor issues (occasional dead IPs, mild geo-inconsistency) | Use with health checks + auto-rotation |
| **C — Probation** | 50–69 | Visible problems — high fraud scores, slow delivery, inconsistent speeds | Use only for DC/ISP, block residential/mobile |
| **D — Rejected** | 0–49 | Failed core requirements | Do not onboard; blacklist for 90 days |

---

## Test Categories & Scoring (100 points total)

### 1. IP Quality (40 pts)

| Check | Method | Pass | Fail |
|-------|--------|------|------|
| Fraud score | IPQS `fraud_score` | ≤50 = 40pts, 51–75 = 20pts, >75 = 0pts | >75 or no response |
| Proxy/VPN detection | IPQS `is_proxy`, `is_vpn` | Both false = 20pts, one true = 10pts, both true = 0pts | Any VPN on residential plan |
| Recent abuse history | IPQS `recent_abuse` | False = 20pts | True = 0pts |
| Datacenter on residential plan | IPQS `is_datacenter` vs plan type | Match = 20pts | DC IP on residential plan = 0pts |

**Scoring:**
- Residential/Mobile plans: reject `is_datacenter=true` outright (Tier D)
- ISP/Datacenter plans: `is_datacenter=true` is expected, no penalty

### 2. Delivery & Reliability (30 pts)

| Check | Method | Pass | Fail |
|-------|--------|------|------|
| Delivery time | Provider API latency | <60s = 15pts, 60–300s = 8pts, >300s = 0pts | Timeout |
| IP aliveness | TCP connect to IP:port | All alive = 15pts, >80% alive = 8pts, <80% = 0pts | <80% |
| Geo accuracy | IP geolocation vs ordered country | Match = 15pts, adjacent region = 5pts, wrong continent = 0pts | Mismatch |

### 3. Performance (20 pts)

| Check | Method | Pass | Fail |
|-------|--------|------|------|
| Speed test | curl via proxy to ipinfo.io | <2s = 10pts, 2–5s = 5pts, >5s = 0pts | Timeout |
| Protocol support | HTTP CONNECT / SOCKS5 handshake | Both = 10pts, one = 5pts, neither = 0pts | Handshake fail |

### 4. Operational (10 pts)

| Check | Method | Pass | Fail |
|-------|--------|------|------|
| API stability | 3 sequential API calls | All succeed = 10pts, 2/3 = 5pts, <2/3 = 0pts | Consistent failures |
| Support responsiveness | Test support ticket (if applicable) | <24h response = 5pts, >24h = 0pts | No response |

---

## Testing Procedure

### Phase 1 — Pre-Onboarding (before adding provider to Styxproxy)

```bash
# Run provider_test.py against trial IPs
python3 backend/app/services/provider_test.py \
  --provider <provider-name> \
  --country Nigeria \
  --type residential \
  --count 5
```

1. Provision 5 trial proxies (residential, Nigeria)
2. Run all benchmark checks
3. Score and classify
4. If Tier A or B: proceed with onboarding checklist
5. If Tier C: document concerns, require sign-off from Dannion
6. If Tier D: do not onboard, log reason in `docs/BLOCKED_PROVIDERS.md`

### Phase 2 — Post-Onboarding Monitoring (ongoing)

```bash
# Run in production, uses real customer IPs
python3 backend/app/services/provider_test.py \
  --provider <provider-name> \
  --mode live \
  --sample 10
```

- Sample 10 active proxies weekly
- If average score drops >15 points from baseline → alert Dannion
- If score enters lower tier → trigger provider review

---

## Score Reporting

`provider_test.py` outputs:

```
Provider: Rayobyte
Country:  Nigeria
Type:     Residential
Tests:    5 IPs, 20 checks

IP Quality:  32/40  ████████░░
Delivery:    25/30  ████████░░
Performance: 18/20  █████████░
Operational:  8/10  ████████░░
─────────────────────────────
TOTAL:       83/100  Tier B — Approved

Flagged IPs:
  185.199.228.45  fraud_score=82 (high)
  185.199.228.46  is_proxy=true (open proxy)
```

---

## Decision Triggers

| Condition | Action |
|-----------|--------|
| Any IP with fraud_score > 85 | Auto-reject that IP, flag in audit log |
| >20% IPs with fraud_score > 75 | Pause new orders from this provider |
| Delivery time > 5 minutes | Alert Dannion, consider Tier C |
| Score drops from A→B or B→C | Review ticket queue, check for patterns |
| Score enters Tier D | Disable provider, notify affected customers |
