# Grafana Loki — Centralised Logging

> Architecture: Grafana Alloy (Interserver) → Loki (Contabo:84.247.132.12:3100) → Grafana (Contabo:84.247.132.12:3000)

## Live Endpoints

- **Grafana**: http://84.247.132.12:3000 (admin / styxgrafana)
- **Loki API**: http://84.247.132.12:3100

## Grafana Queries (LogQL)

```logql
// All API errors
{service="styxproxy-api"} |= "ERROR"

// Charon escalations
{service="styxproxy-api"} |= "charon.escalation"

// Slow requests (>1000ms)
{service="styxproxy-api"} | json | elapsed_ms > 1000

// Dante auth failures
{service="dante-auth"} |= "error"

// Container logs (all)
{container=~"styxproxy-.*"}

// Charon A/B experiment results
{experiment_variant=~"control|treatment"}
```

## Dashboards to Create

1. **API Health** — ERROR rate, slow requests, 5xx/minute
2. **Charon Performance** — escalation rate, resolution rate by A/B variant
3. **Dante SOCKS** — auth failures, connections, bandwidth
4. **Container Overview** — all styxproxy containers

## Interserver: Start Alloy Log Shipper

After Interserver container restart:

```bash
# Download Alloy
ALLOY_VERSION="1.3.0"
curl -sL "https://github.com/grafana/alloy/releases/download/v${ALLOY_VERSION}/alloy-linux-amd64.zip" -o /tmp/alloy.zip
unzip -q /tmp/alloy.zip -d /tmp/
mv /tmp/alloy-linux-amd64 /opt/styxproxy/alloy/alloy
chmod +x /opt/styxproxy/alloy/alloy

# Start service
ln -sf /opt/styxproxy/repo/backend/systemd/styxproxy-alloy.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable styxproxy-alloy && systemctl start styxproxy-alloy

# Verify
curl -s localhost:12345/api/v1/status/config | head -5
```

## Contabo: Loki + Grafana (already running)

- Loki: http://84.247.132.12:3100 (Docker container styxproxy-loki)
- Grafana: http://84.247.132.12:3000 (admin / styxgrafana)
- Promtail: /usr/local/bin/promtail (Docker logs + cron logs)

## Key Files

| File | Host | Purpose |
|---|---|---|
| /opt/styxproxy/alloy/alloy | Interserver | Alloy binary |
| /opt/styxproxy/alloy/config.alloy | Interserver | Loki push config (→ Contabo) |
| /opt/styxproxy/loki-data/ | Contabo | Loki chunks + index |
| /opt/styxproxy/grafana-data/ | Contabo | Grafana dashboards |
| /tmp/promtail-config.yaml | Contabo | Promtail (Docker logs) |
