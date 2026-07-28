#!/bin/bash
# Styxproxy Newman Test Runner
# SECURITY: Test credentials are NOT hardcoded in this file. They must be set in the
# caller's environment (e.g., sourced from /root/.hermes/.env) before invoking this script.
set -e
COLLECTION="/root/styxproxy/postman/styxproxy-auth-tests.postman_collection.json"
REPORT_DIR="/root/styxproxy/postman/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$REPORT_DIR"
ENV_FILE="${STYXPROXY_TEST_ENV:-/root/.hermes/.env}"
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Set STYXPROXY_TEST_ENV to point at your env file." >&2
    exit 1
fi
set -a; source "$ENV_FILE"; set +a
for v in ADMIN_TOKEN TOTP_SECRET ADMIN_PHONE ADMIN_PIN; do
    if [ -z "${!v:-}" ]; then
        echo "ERROR: $v not set in $ENV_FILE" >&2
        exit 2
    fi
done
cat > "$REPORT_DIR/env.json" << ENVEOF
{
  "id": "styxproxy-test-env",
  "name": "Styxproxy Test Environment",
  "values": [
    { "key": "BASE_URL", "value": "https://styxproxy.com/api-proxy", "type": "default" },
    { "key": "ADMIN_TOKEN", "value": "$ADMIN_TOKEN", "type": "default" },
    { "key": "TOTP_SECRET", "value": "$TOTP_SECRET", "type": "default" },
    { "key": "ADMIN_PHONE", "value": "$ADMIN_PHONE", "type": "default" },
    { "key": "ADMIN_PIN", "value": "$ADMIN_PIN", "type": "default" },
    { "key": "ADMIN2_PHONE", "value": "2349012345678", "type": "default" },
    { "key": "ADMIN2_PIN", "value": "5678", "type": "default" },
    { "key": "access_token", "value": "", "type": "default" },
    { "key": "step_token", "value": "", "type": "default" },
    { "key": "invite_code_admin2", "value": "", "type": "default" }
  ],
  "_postman_variable_scope": "environment",
  "_postman_exported_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
ENVEOF
newman run "$COLLECTION" \\
  --environment "$REPORT_DIR/env.json" \\
  --reporters cli,html \\
  --reporter-html-export "$REPORT_DIR/styxproxy-report-$TIMESTAMP.html" \\
  --reporter-json-export "$REPORT_DIR/styxproxy-report-$TIMESTAMP.json" \\
  --timeout 30000
