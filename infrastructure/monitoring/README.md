# Styxproxy Monitoring Stack

Grafana + Loki on the Interserver VPS, fronted by nginx over HTTPS.

| Service | Container | Bind | Public URL |
|---|---|---|---|
| Grafana | `styxproxy-grafana` (11.6.0) | `127.0.0.1:3000` | https://grafana.styxproxy.com |
| Loki | `styxproxy-loki` (3.3.2) | `127.0.0.1:3100` | https://loki.styxproxy.com |

Log ingestion is handled by **Alloy** (`/opt/styxproxy/alloy/`) reading
`/var/log/styxproxy-*.log` and pushing to Loki.

## ⚠️ Both services MUST bind to loopback

Docker writes its own iptables rules that **bypass UFW**. A compose entry of
`ports: ["3100:3100"]` publishes on `0.0.0.0` no matter what the firewall says,
and **Loki ships with `auth_enabled: false`** — no authentication at all. That
combination served production API logs to anyone who knew the IP.

Keep both on `127.0.0.1` and let nginx handle public access.

## Deploy

```bash
cd /opt/styxproxy/monitoring
# compose reads GRAFANA_ADMIN_PASSWORD from a .env BESIDE THIS FILE
printf 'GRAFANA_ADMIN_PASSWORD=%s\n' "$(openssl rand -base64 24)" > .env
chmod 600 .env
docker compose up -d
```

## Two provisioning gotchas

1. **Dashboard JSON must be a bare dashboard object.** A file wrapped as
   `{"dashboard": {...}}` (the Grafana export/API shape) fails with
   `Dashboard title cannot be empty`. Provisioning expects the inner object at
   the top level.

2. **The dashboards directory must be mounted.** Without
   `./grafana/dashboards:/var/lib/grafana/dashboards` the provider logs
   `stat /var/lib/grafana/dashboards: no such file or directory` on a loop and
   no dashboard ever appears.

## `GF_SECURITY_ADMIN_PASSWORD` only applies on FIRST volume init

Recreating the container against an existing `grafana-data` volume does **not**
change the admin password — Grafana seeds it once when the database is created.
Rotate it through the API instead:

```bash
curl -X PUT http://127.0.0.1:3000/api/admin/users/1/password \
  -H 'Content-Type: application/json' -u "admin:<current>" \
  -d '{"password":"<new>"}'
```

## Loki has no web UI

`https://loki.styxproxy.com/` returns `404 page not found` **even when healthy
and authenticated** — there is no dashboard. The domain exists for CLI and
script access (`logcli`, exporters, the Grafana datasource). **Browse logs in
Grafana → Explore → Loki.**

Log labels for this stack: `environment`, `filename`, `host`, `service`,
`service_name`. Query with `{service_name="styxproxy-api"}` — `{app="..."}`
returns nothing.

## Grafana MCP

The Grafana MCP must be the **OSS `grafana/mcp-grafana`** server, not
`https://mcp.grafana.com/mcp`. The Cloud endpoint only accepts Grafana Cloud
stacks and rejects a self-hosted URL with *"not a known Grafana Cloud
instance"*. Authenticate the OSS server with a **service account token**
(`glsa_...`, role Viewer), not OAuth.
