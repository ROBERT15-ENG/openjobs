#!/usr/bin/env bash
# Smoke test: unauthenticated / wrong-role callers must not read private data.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5700}"
BASE_URL="${BASE_URL%/}"

pass=0
fail=0

check() {
  local name="$1"
  local method="$2"
  local path="$3"
  local expect_code="$4"
  local extra_args=("${@:5}")
  local code
  code=$(curl -s -o /tmp/oj_smoke_body.txt -w '%{http_code}' -X "$method" \
    "${extra_args[@]}" "${BASE_URL}${path}" || true)
  if [[ "$code" == "$expect_code" ]]; then
    echo "PASS $name ($code)"
    pass=$((pass + 1))
  else
    echo "FAIL $name (expected $expect_code, got $code)"
    head -c 200 /tmp/oj_smoke_body.txt 2>/dev/null || true
    echo
    fail=$((fail + 1))
  fi
}

echo "OpenJobs untrusted-user smoke — $BASE_URL"
echo

check "admin stats without token" GET "/api/admin/stats" 401
check "applications without token" GET "/api/applications" 401
check "saved jobs without token" GET "/api/saved_jobs" 401
check "user export without token" GET "/api/user/data-export" 401
check "crm companies without token" GET "/api/crm/companies" 401
check "scrape trigger without token" POST "/api/scrape" 401 -H "Content-Type: application/json" -d '{}'
check "jobs list public" GET "/api/jobs?limit=1" 200

echo
echo "Result: $pass passed, $fail failed"
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
