# Grafana Loki — Centralised Logging

> Architecture: Grafana Alloy log shipper on Interserver → Grafana Cloud Loki → Grafana dashboards

## Overview

All Styxproxy service logs are written as JSON to /var/log/styxproxy-*.log. A Grafana Alloy log shipper tails these files and streams to Grafana Cloud Loki in real time.

Why Alloy? Single static binary, no Docker, ~100MB RAM, binary+config in /opt/styxproxy/alloy/ (persists across container restarts).

## Prerequisites

- Grafana Cloud account (free tier: 50GB/month ingestion)
- Loki data source enabled in Grafana Cloud

## Step 1 — Grafana Cloud: Create Loki Data Source

1. Go to grafana.com → Cloud → your Stack → Connections → Data Sources → Add new → Loki
2. Copy the HTTP URL (e.g. https://logs-prod-XXXX.grafana.net)
3. Create an API key with MetricsPublisher role

Loki push endpoint format:
https://<user>:<api-key>@logs-prod-<instance>.grafana.net/loki/api/v1/push

## Step 2 — Configure Credentials

Add to /opt/styxproxy/.env:
LOKI_URL=https://<user>:<api-key>@logs-prod-XXXX.grafana.net/loki/api/v1/push
LOKI_USERNAME=your-grafana-email
LOKI_PASSWORD=your-api-key

## Step 3 — Install Alloy (already done)

Binary: /opt/styxproxy/alloy/alloy (v1.3.0)
Config: /opt/styxproxy/alloy/config.alloy

Reinstall if needed:
ALLOY_VERSION="1.3.0"
curl -sL "https://github.com/grafana/alloy/releases/download/v${ALLOY_VERSION}/alloy-linux-amd64.zip" -o /tmp/alloy.zip
unzip -q /tmp/alloy.zip -d /tmp/alloy-unpack/
mv /tmp/alloy-unpack/alloy-linux-amd64 /opt/styxproxy/alloy/alloy
chmod +x /opt/styxproxy/alloy/alloy

## Step 4 — Start the Shipper

# After container restart (ephemeral /etc), restore unit:
ln -sf /opt/styxproxy/repo/backend/systemd/styxproxy-alloy.service /etc/systemd/system/styxproxy-alloy.service
systemctl daemon-reload
systemctl enable styxproxy-alloy
systemctl start styxproxy-alloy

Verify:
curl -s localhost:12345/api/v1/status/config | python3 -m json.tool | head -10

## Step 5 — Grafana Queries

API Errors: {service="styxproxy-api"} |= "ERROR"
Charon Escalations: {service="styxproxy-api"} |= "charon.escalation"
Slow Requests: {service="styxproxy-api"} | json | unwrap elapsed_ms

## Log Files Shipped

- /var/log/styxproxy-api.log — FastAPI backend (JSON)
- /var/log/styxproxy-dante-auth.err.log — Dante auth failures
- /var/log/styxproxy-nginx-access.log — HTTP access
- /var/log/styxproxy-fulfillment-worker.err.log — Proxy provisioning errors

## Alerting

Set up Grafana-managed alerts:
- API Error Spike: >5 ERROR logs in 1 min
- Dante Auth Failure Rate: >10 failures in 5 min
- Charon Escalation Rate: >3 escalations in 10 min

## Troubleshooting

systemctl status styxproxy-alloy
journalctl -u styxproxy-alloy -f --no-pager

# If log inode changes (rotation), restart:
systemctl restart styxproxy-alloy
