#!/bin/bash

echo "🧪 Testando simulador F5 em produção..."

BASE_URL="https://f5.mmagalha.com"
USERNAME="admin"
PASSWORD="f5password"

echo "1️⃣ Testando login para obter token..."
LOGIN_RESPONSE=$(curl -s -k -X POST "$BASE_URL/mgmt/shared/authn/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\",\"loginProviderName\":\"tmos\"}")

echo "📄 Login Response:"
echo "$LOGIN_RESPONSE" | jq '.' 2>/dev/null || echo "$LOGIN_RESPONSE"

# Extrair token usando jq se disponível, senão usar grep/sed
if command -v jq >/dev/null 2>&1; then
    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.token.token // empty')
else
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*"' | head -1 | sed 's/"token":"\([^"]*\)"/\1/')
fi

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "❌ Falha ao extrair token do login"
    exit 1
fi

echo "🔑 Token extraído: $TOKEN"

echo ""
echo "2️⃣ Testando Basic Authentication..."
BASIC_RESPONSE=$(curl -s -k -u "$USERNAME:$PASSWORD" "$BASE_URL/mgmt/tm/sys")
echo "📄 Basic Auth Response:"
echo "$BASIC_RESPONSE" | jq '.' 2>/dev/null || echo "$BASIC_RESPONSE"

echo ""
echo "3️⃣ Testando Token Authentication..."
TOKEN_RESPONSE=$(curl -s -k -H "X-F5-Auth-Token: $TOKEN" "$BASE_URL/mgmt/tm/sys")
echo "📄 Token Auth Response:"
echo "$TOKEN_RESPONSE" | jq '.' 2>/dev/null || echo "$TOKEN_RESPONSE"

echo ""
echo "4️⃣ Testando informações do token..."
TOKEN_INFO_RESPONSE=$(curl -s -k "$BASE_URL/mgmt/shared/authz/tokens/$TOKEN")
echo "📄 Token Info Response:"
echo "$TOKEN_INFO_RESPONSE" | jq '.' 2>/dev/null || echo "$TOKEN_INFO_RESPONSE"

echo ""
echo "✅ Teste completo!"