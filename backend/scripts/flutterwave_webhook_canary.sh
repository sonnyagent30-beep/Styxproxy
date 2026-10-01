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
# indistinguishable from gateway traffic: every self-originated call is a
# hand-rolled curl against a qa-*@styxproxy.local order. Every count below is
# reported WITH its origin table, or it is not a finding.
#
# ── CORRECTION 2026-10-01 (kanban t_4271b61e) ─────────────────────────────────
# An earlier version of this script reported that no log source recorded a
# client IP for the webhook route, and told the reader that a blank origin
# section meant the canary could not be trusted. That diagnosis was wrong on
# both counts, and pointed at the wrong files:
#
#   - `journalctl -u styxproxy-api` contains NO application output at all,
#     because the unit sets StandardOutput=append:/var/log/styxproxy-api.log.
#     This is true of every route, not just webhooks.
#   - /var/log/nginx/access.log has no webhook lines because the
#     api.styxproxy.com server block overrides it with its own
#     access_log /var/log/styxproxy-nginx-access.log.
#
# Both files DO carry origin, and the middleware already logged `client` on the
# "Request started" line. The genuine gaps, since closed by t_4271b61e, were:
#   1. no `client` on the "Request completed" line (the one you read when
#      investigating a rejection),
#   2. no origin on any handler log line or audit row, and
#   3. NO audit row at all on the 401 rejection paths — so a bad secret
#      produced the same silence as "no traffic ever arrived".
#
# t_4271b61e adds `*_webhook_rejected` audit rows (section 2a) carrying
# origin_scope, which is what now distinguishes a rejected event from an absent
# one. Raw IPs are never persisted: rows carry a SHA-256 pseudonym plus a
# coarse scope, per the customer_hash convention in services/audit.py.
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
# flutterwave_webhook_replay_rejected is retained as the event name for
# implausible-timestamp rejections (was: "outside replay window", 300s cap).
# Since kanban t_c33b5e96 there is NO age cap, so a non-zero count here now means
# a genuinely impossible timestamp (missing/unparseable/future-dated), NOT a slow
# gateway retry. A count that used to mean "payments were being discarded" now
# means something much rarer — if it is non-zero on live traffic, read the rows.
ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
  "sudo -u postgres psql -d $DB -At -F'|' -c \"
    select event_type, count(*) from customer_audit_log
    where event_type in ('webhook_charge.completed','payment.fulfilled','flutterwave_webhook_replay_rejected','paystack_webhook_charge.success')
    group by event_type order by event_type;\""

echo
echo "--- 2. ORIGIN SPLIT: source IPs hitting the webhook route ---"
echo "    (only self-originated traffic = NO live gateway event yet)"
ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
  "echo '  -- api log (/var/log/styxproxy-api.log) --';
   grep 'Request started' /var/log/styxproxy-api.log 2>/dev/null \
     | grep '/api/webhooks/' \
     | grep -oE '\"client\": \"[^\"]+\"' | sort | uniq -c | sort -rn | head -20;
   echo '  -- nginx log (/var/log/styxproxy-nginx-access.log) --';
   grep 'webhooks/' /var/log/styxproxy-nginx-access.log 2>/dev/null \
     | awk '{print \$1}' | sort | uniq -c | sort -rn | head -20"
echo "    NOTE: 127.0.0.1 is nginx on this host, not a gateway. So is the host's"
echo "    own egress IP. A non-self IP here means an external caller reached the"
echo "    route — before any charge, that is worth a look."

echo
echo "--- 2a. REJECTED events — the signal that catches a bad secret ---"
# This is the case the canary exists for: traffic WAS attempted and we said no.
# A wrong FLUTTERWAVE_WEBHOOK_SECRET yields 401s and no charge.completed rows,
# which without these rows looks identical to "no traffic at all".
#   scope=public     -> not us: an external caller
#   scope=self_host/private/loopback -> our own curl, not evidence of anything
#   via=x-real-ip    -> nginx's $remote_addr; NOT client-settable, so trustworthy
#   via=xff          -> came from X-Forwarded-For, which a client CAN set, so it
#                       proves the route was reached but NOT who reached it.
#                       Only reachable when nginx is bypassed (direct to :8000).
ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
"sudo -u postgres psql -d $DB -At -F'|' -c \"
    select event_type,
           coalesce(details->>'reason','-') as reason,
           coalesce(details->>'origin_scope','-') as scope,
           coalesce(details->>'origin_via','-') as via,
           count(*), max(timestamp)
    from customer_audit_log
    where event_type like '%webhook_rejected'
    group by 1,2,3,4 order by 6 desc;\""

echo
echo "--- 2b. NEW audit rows since the snapshot (the primary signal) ---"
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
           coalesce(o.customer_phone,'-'), coalesce(o.status,'-'),
           coalesce(a.details->>'origin_scope','-')
    from customer_audit_log a
    left join orders o on o.payment_reference = a.details->>'tx_ref'
    where a.event_type like 'webhook_%' or a.event_type like 'flutterwave%'
    order by a.timestamp desc limit 15;\""

echo
echo "--- 4. Access-log line counts ---"
ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
  "for f in /var/log/styxproxy-api.log /var/log/styxproxy-nginx-access.log \
            /var/log/nginx/access.log; do
     [ -f \"\$f\" ] && echo \"\$f: \$(wc -l < \"\$f\") lines\"
   done
   echo 'webhook lines in nginx log:'
   grep -c 'webhooks/' /var/log/styxproxy-nginx-access.log 2>/dev/null || echo 0"

echo
echo "--- 5. Verdict ---"
# The verdict is driven by audit rows, not by a log grep.
if [ "$PHASE" = "verify" ]; then
  NEWROWS=$(ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
    "sudo -u postgres psql -d $DB -At -c \"
      select count(*) from customer_audit_log
      where event_type = 'webhook_charge.completed'
        and timestamp > now() - interval '15 minutes';\"" 2>/dev/null || echo 0)

  REJECTS=$(ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$HOST" \
    "sudo -u postgres psql -d $DB -At -c \"
      select count(*) from customer_audit_log
      where event_type = 'flutterwave_webhook_rejected'
        and details->>'origin_scope' = 'public'
        and timestamp > now() - interval '15 minutes';\"" 2>/dev/null || echo 0)

  if [ "${NEWROWS:-0}" -gt 0 ]; then
    echo "SIGNAL PRESENT: $NEWROWS webhook_charge.completed row(s) in the last 15min."
    echo "  -> Cross-check section 3: is the tx_ref a REAL customer order, or a"
    echo "     @styxproxy.local QA order? Only a real customer order proves the"
    echo "     live gateway event got in."
  elif [ "${REJECTS:-0}" -gt 0 ]; then
    # NOTE ON WHAT THIS DOES AND DOES NOT PROVE.
    # origin_scope='public' means an address that is not one of ours reached the
    # route. It does NOT prove the payment gateway did: a caller can still forge
    # X-Forwarded-For on the direct-to-:8000 path, which carries no X-Real-IP,
    # and be classified public. Since t_4271b61e prefers X-Real-IP ($remote_addr,
    # not client-settable), that forgery is only reachable when nginx is bypassed
    # — but it is not impossible, so this verdict states it rather than
    # overclaiming. Confirm against section 2a/3 and the nginx log before
    # declaring a secret rotation broken.
    echo "REJECTED, NOT SILENT: $REJECTS non-self flutterwave_webhook_rejected"
    echo "  row(s) in the last 15min. SOMETHING non-self reached the route and we"
    echo "  returned 401."
    echo "  -> Strongest suspect is still a FLUTTERWAVE_WEBHOOK_SECRET that does not"
    echo "     match the gateway. Before acting on that, confirm the caller was the"
    echo "     GATEWAY and not a forged-header probe: check origin_via in section 2a"
    echo "     ('x-real-ip' is nginx's \$remote_addr and cannot be forged from"
    echo "     outside; 'xff' means the address came from a client-settable header"
    echo "     and is NOT proof of who called), and compare section 2 with"
    echo "     /var/log/styxproxy-nginx-access.log, whose \$remote_addr is not"
    echo "     spoofable. Only a 'x-real-ip' row from a known Flutterwave range is"
    echo "     a genuine gateway rejection."
  else
    echo "NO SIGNAL: zero webhook_charge.completed and zero non-self rejection"
    echo "  rows in the last 15 minutes."
    echo "  UNVERIFIED, not a pass. No external caller reached this route at all,"
    echo "  so this cannot distinguish 'no charge made yet' from 'gateway never"
    echo "  got through'. If you are certain a real charge was made, check"
    echo "  section 2: if no non-self IP appears there either, the event never"
    echo "  reached this host (DNS/CDN/firewall), so the secret is NOT implicated."
  fi
else
  echo "Snapshot taken. Re-run with 'verify' within 15min of the first live charge."
  echo "Compare section 1/2b counts against this snapshot."
fi
