#!/usr/bin/env bash
# Flutterwave webhook canary — kanban t_604d405d
#
# Run IMMEDIATELY BEFORE rotating FLUTTERWAVE_WEBHOOK_SECRET in .env, then
# again within MINUTES of the first live charge. Rotation makes the next
# genuine charge.completed the first live gateway event this platform has ever
# let in. There is no prior art, so there is exactly one shot at observing it.
#
# WHY THE ORIGIN SPLIT IS MANDATORY
# A bare webhook count is unverified. Production logs contain test traffic
# indistinguishable from gateway traffic: the single non-self 200 from
# 102.89.33.53 was a hand-rolled curl against a qa-webhook-final@styxproxy.local
# order. Every count below is reported WITH its origin table, or it is not a
# finding.
set -uo pipefail

SSH_KEY="${SSH_KEY:-$HOME/.ssh/styxproxy-interserver}"
HOST="${HOST:-root@162.35.184.69}"
DB="${DB:-styxproxy}"
PHASE="${1:-snapshot}"   # snapshot | verify

echo "=============================================================="
echo " Flutterwave webhook canary — phase: $PHASE"
echo " $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=============================================================="

echo
echo "--- 1. Audit-row counts (event_type) ---"
ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
  "sudo -u postgres psql -d $DB -At -F'|' -c \"
    select event_type, count(*) from customer_audit_log
    where event_type in ('webhook_charge.completed','payment.fulfilled','flutterwave_webhook_replay_rejected','paystack_webhook_charge.success')
    group by event_type order by event_type;\""

echo
echo "--- 2. ORIGIN SPLIT: non-self source IPs hitting the webhook route ---"
echo "    (a webhook row with only self-originated traffic = NO live event yet)"
# NOTE: as of this writing neither uvicorn's journal nor nginx's access.log
# records a client IP for /api/webhooks/*. Verified on prod 2026-10-01:
#   - journalctl -u styxproxy-api shows no client/remote field at all
#   - nginx access.log has 0 lines matching 'webhooks/flutterwave'
# So this section CAN legitimately come back empty on a healthy system, and an
# empty result here is NOT evidence of a working secret. Section 2b is the
# signal that actually exists; if 2b is also empty, treat the canary as
# UNVERIFIED rather than as a pass, and add client-IP logging first.
ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
  "journalctl -u styxproxy-api --since '-6h' --no-pager 2>/dev/null \
   | grep -oE '\"(client_host|origin_ip|remote_addr|client)\": *\"?[0-9a-fA-F.:]+\"?' \
   | grep -oE '[0-9a-fA-F.:]+\$?' | sort | uniq -c | sort -rn | head -20"
echo "    (if the above is blank, see note — blank is NOT a pass)"

echo
echo "--- 2b. NEW audit rows since the snapshot (the signal that exists) ---"
# webhook_charge.completed rows are the ground truth. Comparing the count
# before rotation against the count now tells us whether a live event landed.
ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
  "sudo -u postgres psql -d $DB -At -F'|' -c \"
    select event_type, count(*), max(timestamp) from customer_audit_log
    where event_type in ('webhook_charge.completed','payment.fulfilled')
    group by event_type order by event_type;\""

echo
echo "--- 3. Most recent webhook rows, with the evidence that distinguishes"
echo "       real gateway traffic from our own QA curls ---"
# orders.customer_phone is the discriminator: every QA/test order carries an
# @styxproxy.local anon address. A row whose tx_ref maps to a real customer
# order is the canary signal; a qa-* / *-test ref is ours.
ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
  "sudo -u postgres psql -d $DB -At -F'|' -c \"
    select a.event_type, a.timestamp, coalesce(o.order_id,'(no order)'),
           coalesce(o.customer_phone,'-'), coalesce(o.status,'-')
    from customer_audit_log a
    left join orders o on o.payment_reference = a.details->>'tx_ref'
    where a.event_type like 'webhook_%' or a.event_type like 'flutterwave%'
    order by a.timestamp desc limit 15;\""

echo
echo "--- 4. Access-log line count (access.log / uvicorn) ---"
ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
  "for f in /var/log/nginx/access.log /opt/styxproxy/backend/access.log; do
     [ -f \"\$f\" ] && echo \"\$f: \$(wc -l < \"\$f\") lines\"
   done"

echo
echo "--- 5. Verdict ---"
# The verdict is driven by NEW customer_audit_log rows, not by a log grep.
# Grepping for a non-self IP cannot work today (see the note in section 2).
if [ "$PHASE" = "verify" ]; then
  NEWROWS=$(ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
    "sudo -u postgres psql -d $DB -At -c \"
      select count(*) from customer_audit_log
      where event_type = 'webhook_charge.completed'
        and timestamp > now() - interval '15 minutes';\"" 2>/dev/null || echo 0)

  if [ "${NEWROWS:-0}" -gt 0 ]; then
    echo "SIGNAL PRESENT: $NEWROWS webhook_charge.completed row(s) in the last 15min."
    echo "  -> Cross-check section 3: is the tx_ref a REAL customer order, or a"
    echo "     @styxproxy.local QA order? Only a real customer order proves the"
    echo "     live gateway event got in."
  else
    echo "NO SIGNAL: zero webhook_charge.completed rows in the last 15 minutes."
    echo "  UNVERIFIED, not a pass — this canary cannot currently distinguish"
    echo "  'no traffic yet' from 'secret rejected every event', because no log"
    echo "  source records the origin IP for this route."
    echo "  If a real charge was made and nothing landed, the configured secret"
    echo "  does NOT match the gateway. Surface this NOW, not at the next standup."
    echo "  Recommended: add client-IP logging to the webhook route before rotation."
  fi
else
  echo "Snapshot taken. Re-run with 'verify' within 15min of the first live charge."
  echo "Compare section 1/2b counts against this snapshot."
fi