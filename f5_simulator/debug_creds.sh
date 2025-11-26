#!/bin/bash

echo "🔍 Verificando credenciais do simulador F5..."

BASE_URL="https://f5.mmagalha.com"

echo "1️⃣ Testando endpoint raiz para ver credenciais padrão..."
ROOT_RESPONSE=$(curl -s -k "$BASE_URL/")
echo "📄 Root Response:"
echo "$ROOT_RESPONSE" | jq '.' 2>/dev/null || echo "$ROOT_RESPONSE"

echo ""
echo "2️⃣ Testando login com senha 'admin'..."
LOGIN_ADMIN=$(curl -s -k -X POST "$BASE_URL/mgmt/shared/authn/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin","loginProviderName":"tmos"}')
echo "📄 Response com senha 'admin':"
echo "$LOGIN_ADMIN" | jq '.' 2>/dev/null || echo "$LOGIN_ADMIN"

echo ""
echo "3️⃣ Testando login com senha 'f5password'..."
LOGIN_F5PASS=$(curl -s -k -X POST "$BASE_URL/mgmt/shared/authn/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"f5password","loginProviderName":"tmos"}')
echo "📄 Response com senha 'f5password':"
echo "$LOGIN_F5PASS" | jq '.' 2>/dev/null || echo "$LOGIN_F5PASS"

echo ""
echo "4️⃣ Verificando pods do simulador..."
kubectl get pods -n f5-simulator

echo ""
echo "5️⃣ Verificando variáveis de ambiente do pod..."
POD_NAME=$(kubectl get pods -n f5-simulator -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ ! -z "$POD_NAME" ]; then
    echo "📋 Pod encontrado: $POD_NAME"
    kubectl exec -n f5-simulator "$POD_NAME" -- env | grep F5_
else
    echo "❌ Nenhum pod encontrado"
fi