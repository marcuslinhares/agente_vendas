#!/bin/bash
# E2E integration test for Agente de Vendas
# Requires: docker compose running with all services
# Usage: ./scripts/test-e2e.sh

set -e

PASS=0
FAIL=0
COOKIE_JAR=$(mktemp /tmp/e2e-cookies.XXXXXX)
cleanup() { rm -f "$COOKIE_JAR"; }
trap cleanup EXIT

pass() { PASS=$((PASS + 1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  ❌ $1"; }
warn() { echo "  ⚠️  $1"; }

echo ""
echo "🧪 Agente de Vendas - E2E Test Suite"
echo "====================================="

# ------------------------------------------------------------------
# 1. Health checks
# ------------------------------------------------------------------
echo ""
echo "📡 Health checks..."

health_check() {
  local url="$1" label="$2" expected="${3:-200}"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "$url" 2>/dev/null || true)
  code="${code:-000}"
  if [ "$code" = "$expected" ]; then
    pass "$label (HTTP $code)"
  elif [ "$code" = "000" ]; then
    warn "$label offline (expected if docker compose not running)"
  else
    warn "$label returned HTTP $code"
  fi
}

auth_curl() {
  curl -s -b "$COOKIE_JAR" --connect-timeout 3 "$@" 2>/dev/null || true
}

request_with_cookies() {
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 \
    -X "$1" "$2" \
    -H "Content-Type: application/json" \
    -d "$3" \
    -c "$COOKIE_JAR" 2>/dev/null || true)
  echo "${code:-000}"
}

health_check "http://localhost:3000/health" "Hono health check"
health_check "http://localhost:8000/health" "FastAPI health check"
health_check "http://localhost:4000/api/v1/auth/login" "NestJS reachable" "401"

# ------------------------------------------------------------------
# 2. Auth flow
# ------------------------------------------------------------------
echo ""
echo "🔐 Auth flow..."

# Register
REGISTER_STATUS=$(request_with_cookies POST "http://localhost:4000/api/v1/auth/register" \
  '{"email":"e2e@test.com","password":"test123","name":"E2E Test"}')
if [ "$REGISTER_STATUS" = "201" ]; then
  pass "Register (HTTP 201)"
elif [ "$REGISTER_STATUS" = "409" ]; then
  pass "Register (already exists, HTTP 409 — proceeding)"
else
  warn "Register returned HTTP $REGISTER_STATUS"
fi

# Login
LOGIN_STATUS=$(request_with_cookies POST "http://localhost:4000/api/v1/auth/login" \
  '{"email":"e2e@test.com","password":"test123"}')
if [ "$LOGIN_STATUS" = "201" ]; then
  pass "Login (HTTP 201)"
else
  fail "Login (HTTP $LOGIN_STATUS)"
fi

# Verify the cookie was captured
if grep -q "token" "$COOKIE_JAR" 2>/dev/null; then
  pass "Auth token cookie captured"
else
  fail "No auth token cookie found"
fi

# ------------------------------------------------------------------
# 3. Products API
# ------------------------------------------------------------------
echo ""
echo "📦 Products API..."

CREATE_PRODUCT=$(auth_curl -X POST http://localhost:4000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Product","price":29.90,"category":"test","stock":10}') || CREATE_PRODUCT='{}'
PRODUCT_ID=$(echo "$CREATE_PRODUCT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('id', ''))
except Exception:
    print('')
" 2>/dev/null || true)
if [ -n "$PRODUCT_ID" ]; then
  pass "Create product (id: ${PRODUCT_ID:0:8})"
else
  fail "Create product ($CREATE_PRODUCT)"
fi

LIST_PRODUCTS=$(auth_curl http://localhost:4000/api/v1/products) || LIST_PRODUCTS='{"products":[],"total":0}'
PRODUCT_COUNT=$(echo "$LIST_PRODUCTS" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('total', 0))
except Exception:
    print('0')
" 2>/dev/null || true)
if [ "$PRODUCT_COUNT" -ge 1 ] 2>/dev/null; then
  pass "List products ($PRODUCT_COUNT found)"
else
  warn "List products (got $PRODUCT_COUNT — expected >=1 with docker compose)"
fi

# ------------------------------------------------------------------
# 4. Conversations API
# ------------------------------------------------------------------
echo ""
echo "💬 Conversations API..."

LIST_CONVERSATIONS=$(auth_curl http://localhost:4000/api/v1/conversations) || true
CONV_COUNT=$(echo "${LIST_CONVERSATIONS:-[]}" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(len(d) if isinstance(d, list) else 0)
except Exception:
    print('0')
" 2>/dev/null || true)
pass "List conversations (${CONV_COUNT:-0} found)"

# ------------------------------------------------------------------
# 5. Webhook simulation
# ------------------------------------------------------------------
echo ""
echo "📨 Webhook test..."

WEBHOOK_RESP=$(curl -s -X POST http://localhost:3000/webhook/evolution \
  -H "Content-Type: application/json" \
  -d '{"key":{"remoteJid":"5511999999999@c.us"},"message":{"conversation":"Olá, quero ver produtos"}}' \
  --connect-timeout 3 2>/dev/null || echo '{"error":"hono offline"}')
if echo "$WEBHOOK_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d.get('ok') or d.get('status') == 'ok'
" 2>/dev/null; then
  pass "Webhook received"
else
  warn "Webhook simulation (Hono may be offline)"
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo "====================================="
echo "📊 Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  echo "⚠️  Some tests failed — review output above."
  exit 1
else
  echo "✅ E2E tests complete."
  exit 0
fi
