# Data Retention Policy

**Owner:** Styxproxy Operations
**Effective:** 2026-08-09
**Review:** Quarterly

---

## Why This Exists

Data retention keeps the database lean, reduces storage costs, and limits GDPR/NDPR liability by not holding data longer than necessary. Different data types have different lifespans.

---

## Retention Schedule

| Table / Data Type | Retention | Rationale |
|---|---|---|
| `analytics_events` | **30 days** raw → summarise to monthly | Raw events grow fast; monthly summaries preserve trends |
| `health_snapshots` | **30 days** | Operational health data; 30 days covers most debugging windows |
| `admin_audit_log` | **2 years** | Security audit trail; sensitive |
| `charon_ab_assignments` | **90 days** | A/B test data; 90 days enough for analysis |
| `charon_ab_outcomes` | **90 days** | A/B test outcomes; linked to assignments |
| `charon_escalations` | **90 days** | Chat escalation logs |
| `charon_context` | **7 days** | Temporary conversation context |
| `charon_blog_chunks` | **180 days** | Blog cache; refreshes on crawl |
| `contact_submissions` | **2 years** | Customer enquiries (NDPR) |
| `support_messages` | **2 years** | Support thread history |
| `customers` | **Until deletion** | Customer account; deleted on request |
| `orders` | **7 years** | Financial records (Nigeria FIRS requirement) |
| `posts`, `post_categories` | **Until unpublished** | Blog content; removed when post deleted |
| `email_unsubscribes` | **Permanent** | Suppression list; re-subscribes allowed |
| `processed_webhooks` | **30 days** | Idempotency cache; not needed beyond 30 days |
| `idempotency_responses` | **7 days** | Short-lived deduplication |
| `pending_trial_surveys` | **30 days** | Incomplete survey data |

---

## Cron Jobs

All jobs run at **03:00 UTC** daily via `cronjob` tool.

### 1. analytics_events — summarise & trim (daily 03:00)

Summarise yesterday's events into a `monthly_analytics` table, then delete raw rows older than 30 days.

### 2. health_snapshots — trim (daily 03:15)

Delete snapshots older than 30 days.

### 3. admin_audit_log — archive & trim (daily 03:30)

Archive rows older than 1 year to JSON file in `/opt/styxproxy/backups/audit/`, then delete from DB. Keep 2 years online.

### 4. charon context/chunks — purge (daily 04:00)

Delete `charon_context` entries older than 7 days. Delete `charon_blog_chunks` older than 180 days.

### 5. contact_submissions — purge (monthly)

Delete `contact_submissions` older than 2 years (after annual review).

### 6. processed_webhooks / idempotency — purge (daily 03:05)

Delete `processed_webhooks` older than 30 days, `idempotency_responses` older than 7 days.

---

## Cron Job Files

- `/opt/styxproxy/backend/scripts/retention_analytics.py` — analytics summarise + trim
- `/opt/styxproxy/backend/scripts/retention_health.py` — health snapshots trim
- `/opt/styxproxy/backend/scripts/retention_audit.py` — audit log archive + trim
- `/opt/styxproxy/backend/scripts/retention_cleanup.py` — context, webhooks, etc.

---

## Customer Deletion

When a customer requests account deletion (GDPR Article 17 / NDPR):

1. Delete all `customers` rows (cascade deletes `orders`, `styxproxy_credentials`, `contact_submissions`)
2. Delete `support_messages` where `customer_id` matches
3. Delete `analytics_events` where `customer_id` matches
4. Log the deletion in `admin_audit_log`

**Script:** `/opt/styxproxy/backend/scripts/gdpr_delete_customer.py <customer_id>`

---

## Review Schedule

- **Quarterly:** Review retention periods — adjust if regulations change
- **After any new table:** Assign a retention period before it accumulates data
- **Annual:** Audit log of all retention jobs (runs/failures/errors)

---

## Notes

- NDPR (Nigeria Data Protection Regulation, 2020) requires data minimisation and purpose limitation.
- FIRS (Federal Inland Revenue Service) requires financial records for 7 years minimum.
- All deletion is **soft** unless explicitly hard-deleted (customer request = hard delete).
