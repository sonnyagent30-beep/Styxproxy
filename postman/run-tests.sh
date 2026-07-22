#!/bin/bash
# Styxproxy Newman Test Runner — Updated
set -e
COLLECTION="/root/styxproxy/postman/styxproxy-auth-tests.postman_collection.json"
REPORT_DIR="/root/styxproxy/postman/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$REPORT_DIR"

# Step 1: Setup
TOTP_SECRET="Z32632KWXC4X6N3WNFHVJBM5EVUYECRU"
ACCESS_TOKEN="1BLUnmY7gkUnnrh2rg13Ne7c-RgZjf1l"

cat > "$REPORT_DIR/env.json" << ENVEOF
{
  "id": "styxproxy-test-env",
  "name": "Styxproxy Test Environment",
  "values": [
    { "key": "BASE_URL", "value": "https://styxproxy.com/api-proxy", "type": "default" },
    { "key": "ADMIN_TOKEN", "value": "$ACCESS_TOKEN", "type": "default" },
    { "key": "TOTP_SECRET", "value": "$TOTP_SECRET", "type": "default" },
    { "key": "ADMIN_PHONE", "value": "2347032981049", "type": "default" },
    { "key": "ADMIN_PIN", "value": "1234", "type": "default" },
    { "key": "ADMIN2_PHONE", "value": "2349012345678", "type": "default" },
    { "key": "ADMIN2_PIN", "value": "5678", "type": "default" },
    { "key": "access_token", "value": "", "type": "default" },
    { "key": "step_token", "value": "", "type": "default" },
    { "key": "invite_code_admin2", "value": "", "type": "default" }
  ],
  "_postman_variable_scope": "environment",
  "_postman_exported_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "_postman_exported_using": "Newman CLI"
}
ENVEOF

# Step 2: Clean DB and setup
docker exec styxproxy-local-postgres-1 psql -U styxproxy -d styxproxy -c "DELETE FROM admin_invites; DELETE FROM admin_auth; DELETE FROM admin_audit_log;" 2>/dev/null || true

TOTP=$(python3 -c "import pyotp; print(pyotp.TOTP('$TOTP_SECRET').now())")
SETUP=$(curl -s -X POST "https://styxproxy.com/api-proxy/api/admin/auth/setup" \
  -H "Content-Type: application/json" \
  -d "{\"admin_phone\":\"2347032981049\",\"invite_code\":\"$ACCESS_TOKEN\",\"pin\":\"1234\",\"totp_code\":\"$TOTP\"}")
echo "Setup: $SETUP"

ACCESS_TOKEN=$(echo "$SETUP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

if [ -z "$ACCESS_TOKEN" ]; then
  TOTP=$(python3 -c "import pyotp; print(pyotp.TOTP('$TOTP_SECRET').now())")
  STEP1=$(curl -s -X POST "https://styxproxy.com/api-proxy/api/admin/auth/login/step1" \
    -H "Content-Type: application/json" -d '{"admin_phone":"2347032981049","pin":"1234"}')
  STEP_TOKEN=$(echo "$STEP1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('step_token',''))")
  TOTP=$(python3 -c "import pyotp; print(pyotp.TOTP('$TOTP_SECRET').now())")
  LOGIN=$(curl -s -X POST "https://styxproxy.com/api-proxy/api/admin/auth/login/step2" \
    -H "Content-Type: application/json" \
    -d "{\"step_token\":\"$STEP_TOKEN\",\"totp_code\":\"$TOTP\"}")
  ACCESS_TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
fi

python3 -c "
import json
with open('$REPORT_DIR/env.json') as f:
    env = json.load(f)
for v in env['values']:
    if v['key'] == 'access_token':
        v['value'] = '$ACCESS_TOKEN'
        break
with open('$REPORT_DIR/env.json', 'w') as f:
    json.dump(env, f, indent=2)
"
echo "Token: ${ACCESS_TOKEN:0:20}..."

# Step 3: Run Newman
cd "$REPORT_DIR"
newman run "$COLLECTION" \
  --environment ./env.json \
  --reporters cli,htmlextra,json \
  --reporter-htmlextra-export "./styxproxy-report-$TIMESTAMP.html" \
  --reporter-json-export "./styxproxy-report-$TIMESTAMP.json" \
  --timeout-request 10000 \
  --verbose \
  2>&1 | tee "./newman-output-$TIMESTAMP.txt"

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "Reports:"
echo "  HTML: $REPORT_DIR/styxproxy-report-$TIMESTAMP.html"
echo "  JSON: $REPORT_DIR/styxproxy-report-$TIMESTAMP.json"
echo "  Output: $REPORT_DIR/newman-output-$TIMESTAMP.txt"

# Parse JSON report
if [ -f "./styxproxy-report-$TIMESTAMP.json" ]; then
  python3 << PYEOF
import json
with open('$REPORT_DIR/styxproxy-report-$TIMESTAMP.json') as f:
    report = json.load(f)
run = report.get('run', {})
counts = run.get('stats', {}).get('requests', {})
total = counts.get('total', 0)
failed = counts.get('failed', 0)
passed = total - failed
print(f"\nSUMMARY: {passed}/{total} passed, {failed} failed ({round(passed/total*100,1) if total > 0 else 0}%)")
PYEOF
fi

# Clean DB
docker exec styxproxy-local-postgres-1 psql -U styxproxy -d styxproxy -c "DELETE FROM admin_invites; DELETE FROM admin_auth;" 2>/dev/null

exit $EXIT_CODE
