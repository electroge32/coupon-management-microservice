#!/bin/bash
#
# Smoke Test End-to-End (Laravel)
# Verifica el flujo completo del servicio.
#
# Uso:
#   chmod +x tests/smoke_test.sh
#   ./tests/smoke_test.sh
#

set -e

BASE_URL="http://localhost:8000"
API_KEY="${API_KEY:-test-key}"

echo ""
echo "🔥 Smoke Tests E2E — Laravel — $BASE_URL"
echo ""

# T1: Health check
echo "🧪 T1: Health check..."
curl -s "$BASE_URL/api/v1/health" | grep -q '"status"'
echo "✅ T1: Health check OK"

# T2: Auth rejection
echo "🧪 T2: Auth rejection..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/coupons")
[ "$HTTP_CODE" = "401" ]
echo "✅ T2: Auth rejection OK"

# T3: Create birthday coupon (forces amount to 15)
echo "🧪 T3: Birthday coupon creation..."
BD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/coupons" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"type":"birthday","discount_type":"percent","amount":99,"email":"test@example.com"}')
echo "$BD_RESPONSE" | grep -q '"amount":15'
BD_CODE=$(echo "$BD_RESPONSE" | grep -o '"code":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "✅ T3: Birthday coupon created: $BD_CODE"

# T4: Create referral coupon (forces amount to 3000)
echo "🧪 T4: Referral coupon creation..."
REF_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/coupons" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"type":"referral","discount_type":"fixed_cart","amount":9999,"email":"ref@example.com"}')
echo "$REF_RESPONSE" | grep -q '"amount":3000'
REF_CODE=$(echo "$REF_RESPONSE" | grep -o '"code":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "✅ T4: Referral coupon created: $REF_CODE"

# T5: Validate with wrong email fails
echo "🧪 T5: Validate wrong email..."
VAL_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/coupons/$BD_CODE/validate" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"wrong@example.com","product_ids":[]}')
echo "$VAL_RESPONSE" | grep -q '"valid":false'
echo "✅ T5: Validate wrong email OK"

# T6: Validate correct and apply
echo "🧪 T6: Validate and apply..."
VALID_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/coupons/$BD_CODE/validate" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","product_ids":[]}')
echo "$VALID_RESPONSE" | grep -q '"valid":true'

APPLY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/coupons/$BD_CODE/apply" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","order_id":"TEST-123"}')
echo "$APPLY_RESPONSE" | grep -q '"use_count":1'
echo "✅ T6: Validate and apply OK"

# T7: Campaign without expires_at fails
echo "🧪 T7: Campaign requires expiration..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/coupons" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"type":"campaign","discount_type":"percent","amount":20,"prefix":"PROMO"}')
[ "$HTTP_CODE" = "400" ]
echo "✅ T7: Campaign validation OK"

# T8: Campaign with expires_at succeeds
echo "🧪 T8: Campaign creation..."
FUTURE=$(date -d "+7 days" +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -v+7d +%Y-%m-%dT%H:%M:%S)
CAMP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/coupons" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"campaign\",\"discount_type\":\"percent\",\"amount\":20,\"prefix\":\"PROMO\",\"expires_at\":\"$FUTURE\"}")
echo "$CAMP_RESPONSE" | grep -q '"code":"PROMO-'
echo "✅ T8: Campaign creation OK"

# T9: List coupons
echo "🧪 T9: List coupons..."
LIST_RESPONSE=$(curl -s "$BASE_URL/api/v1/coupons" -H "X-API-Key: $API_KEY")
echo "$LIST_RESPONSE" | grep -q '"total":'
echo "✅ T9: List coupons OK"

# T10: Bulk creation
echo "🧪 T10: Bulk creation..."
BULK_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/coupons/bulk" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"quantity":3,"type":"birthday","discount_type":"percent","amount":50,"email":"bulk@example.com"}')
echo "$BULK_RESPONSE" | grep -q '"created":3'
echo "✅ T10: Bulk creation OK"

echo ""
echo "✅ TODOS LOS SMOKE TESTS PASARON"
echo ""
