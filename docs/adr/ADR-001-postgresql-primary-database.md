# ADR-001: PostgreSQL as Primary Database

**Date:** 2026-06-26
**Status:** Accepted
**Deciders:** Sonny (agent), Dannion

---

## Context

Styxproxy started with Google Sheets as the database. At the MVP stage, Sheets works — it's free, zero setup, and easy to share. But Sheets doesn't scale: no real-time triggers, limited API access, concurrent write conflicts, and no structured relationships.

As Styxproxy moves toward a real business with real orders, we need a real database.

---

## Decision

**Use PostgreSQL** as the primary database, self-hosted on the VPS alongside n8n.

---

## Why PostgreSQL

| Factor | Decision |
|--------|---------|
| **n8n native support** | n8n has a built-in PostgreSQL node — no custom code needed |
| **Relational data** | Orders, customers, referrals, alerts all have relationships Sheets can't handle |
| **ACID compliance** | Payment data must be consistent — no concurrent write conflicts |
| **Mature** | Battle-tested, well-documented, easy to operate on VPS |
| **Free** | No SaaS cost — self-hosted on existing VPS |
| **Backup-friendly** | pg_dump + R2 = simple, reliable backup |

**Alternatives considered:**

| Alternative | Why Not |
|-------------|---------|
| MySQL | n8n MySQL node less mature; PostgreSQL is better for JSON + complex queries |
| MongoDB | No relational integrity; too flexible for financial data |
| Supabase (PostgreSQL SaaS) | Adds dependency + cost; self-hosted PostgreSQL is sufficient at this scale |
| Google Sheets | No triggers, concurrent write conflicts, no relationships |
| Airtable | $20+/mo; overkill for starting out |

---

## Consequences

**Positive:**
- Real relational schema: orders → customers → referrals
- ACID transactions for payment processing
- n8n can query and write directly via native nodes
- Structured audit logs
- Scales to thousands of orders without performance issues

**Negative:**
- Self-hosted = self-maintained (backups, updates, security)
- Adds VPS resource usage (PostgreSQL ~100MB RAM)
- Migration from Sheets requires a data import step

**Mitigation:** pgBouncer for connection pooling, automated daily backups via pg_dump to R2.

---

## Implementation

PostgreSQL runs on the same VPS as n8n. Connection via `postgresql://bunche:password@localhost:5432/bunche`. pgBouncer sits in front for connection pooling.

Schema defined in `docs/DATABASE_SCHEMA.md`.

---

## Rollback

If PostgreSQL fails catastrophically, Sheets can be recreated from the `daily_summary` and `orders` data as a last resort. But this is a last resort — PostgreSQL backup + restore is the primary recovery path.
