# Styxproxy Backend Scripts

Author: Oyebiyi Ayomide

## update_trigger_weights.py

Nightly cron job that recalculates trigger weights from the last 7 days of engagement data.

**Run manually:**
```bash
cd /root/styxproxy/backend && python3 scripts/update_trigger_weights.py
```

**Railway cron:** Set up a scheduled job with command `python3 scripts/update_trigger_weights.py` and schedule `0 3 * * *` (3 AM UTC daily).

The script learns from aggregate trigger behavior:
- `positive_rate = (opens + converted × 1.5) / fires`
- `new_weight = clamp(old_weight + 0.10 × signal, 0.2, 3.0)`
- Requires at least 10 data points to run, 20 fires to update weight
