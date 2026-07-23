#!/bin/bash
# Styxproxy Full Regression Suite — runs all Postman collections + scenario checklist.
#
# Exit code 0 = all pass. Non-zero = at least one collection had a failing test.
#
# Usage:
#   ./run-regression.sh                  # full suite
#   ./run-regression.sh public           # just public + customer flows
#   ./run-regression.sh admin            # just admin auth flows
set -e

COLLECTIONS_DIR="/root/styxproxy/postman"
REPORT_DIR="$COLLECTIONS_DIR/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$REPORT_DIR"

TOTP_SECRET="${TOTP_SECRET:-Z32632KWXC4X6N3WNFHVJBM5EVUYECRU}"
ACCESS_TOKEN="${ACCESS_TOKEN:-1BLUnmY7gkUnnrh2rg13Ne7c-RgZjf1l}"

# Shared env — both collections read from this file
cat > "$REPORT_DIR/env.json" << ENVEOF
{
  "id": "styxproxy-test-env",
  "name": "Styxproxy Test Environment",
  "values": [
    { "key": "BASE_URL", "value": "https://api.styxproxy.com", "type": "default" },
    { "key": "ADMIN_TOKEN", "value": "$ACCESS_TOKEN", "type": "default" },
    { "key": "TOTP_SECRET", "value": "$TOTP_SECRET", "type": "default" }
  ],
  "_postman_variable_scope": "environment"
}
ENVEOF

run_collection() {
  local name="$1"
  local file="$2"
  echo ""
  echo "==============================================="
  echo "  Running $name collection"
  echo "==============================================="

  cd "$REPORT_DIR"
  newman run "$COLLECTIONS_DIR/$file" \
    --environment ./env.json \
    --reporters cli,json \
    --reporter-json-export "./${name}-${TIMESTAMP}.json" \
    --timeout-request 15000 \
    --bail=false \
    2>&1 | tee "./${name}-${TIMESTAMP}.txt" | tail -40

  local exit_code=${PIPESTATUS[0]}
  local report_file="$REPORT_DIR/${name}-${TIMESTAMP}.json"

  if [ -f "$report_file" ]; then
    NAME="$name" REPORT="$report_file" python3 - <<'PYEOF'
import json, os
report = json.load(open(os.environ["REPORT"]))
run = report.get("run", {})
counts = run.get("stats", {}).get("requests", {})
total = counts.get("total", 0)
failed = counts.get("failed", 0)
passed = total - failed
pct = round(passed/total*100, 1) if total > 0 else 0
name = os.environ["NAME"]
print(f"\n[{name.upper()}] {passed}/{total} passed, {failed} failed ({pct}%)")
if failed > 0:
    print(f"[{name.upper()}] FAILING REQUESTS:")
    for fail in run.get("failures", []):
        print(f"  - {fail.get('source', {}).get('name', '?')}: {fail.get('error', {}).get('message', '?')}")
PYEOF
  fi

  return $exit_code
}

case "${1:-all}" in
  public)
    run_collection "public" "styxproxy-public.postman_collection.json"
    ;;
  admin)
    run_collection "admin" "styxproxy-auth-tests.postman_collection.json"
    ;;
  all|"")
    PUBLIC_EXIT=0
    ADMIN_EXIT=0
    run_collection "public" "styxproxy-public.postman_collection.json" || PUBLIC_EXIT=$?
    run_collection "admin" "styxproxy-auth-tests.postman_collection.json" || ADMIN_EXIT=$?

    echo ""
    echo "==============================================="
    echo "  REGRESSION SUMMARY"
    echo "==============================================="
    echo "  Public + customer: exit=$PUBLIC_EXIT"
    echo "  Admin + team:      exit=$ADMIN_EXIT"
    echo ""
    echo "  Reports: $REPORT_DIR/{public,admin}-${TIMESTAMP}.{json,txt}"
    echo ""
    echo "  Also see: docs/ACCEPTANCE-CHECKLIST.md (79 scenario checks)"
    if [ $PUBLIC_EXIT -ne 0 ] || [ $ADMIN_EXIT -ne 0 ]; then
      exit 1
    fi
    ;;
  *)
    echo "Usage: $0 [public|admin|all]"
    exit 2
    ;;
esac