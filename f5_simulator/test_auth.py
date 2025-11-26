#!/usr/bin/env python3
"""
Teste de autenticação para o F5 Simulator
"""

import requests
from requests.auth import HTTPBasicAuth
import json

# Configuração do servidor
BASE_URL = "http://localhost:8080"
USERNAME = "admin"
PASSWORD = "admin"

def test_without_auth():
    """Teste sem autenticação - deve falhar"""
    print("🔍 Testando sem autenticação...")
    try:
        response = requests.get(f"{BASE_URL}/mgmt/tm/ltm/pool")
        print(f"❌ Status: {response.status_code} (esperado: 401)")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_wrong_credentials():
    """Teste com credenciais erradas - deve falhar"""
    print("\n🔍 Testando com credenciais erradas...")
    try:
        auth = HTTPBasicAuth("wrong", "credentials")
        response = requests.get(f"{BASE_URL}/mgmt/tm/ltm/pool", auth=auth)
        print(f"❌ Status: {response.status_code} (esperado: 401)")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_correct_credentials():
    """Teste com credenciais corretas - deve funcionar"""
    print("\n🔍 Testando com credenciais corretas...")
    try:
        auth = HTTPBasicAuth(USERNAME, PASSWORD)
        response = requests.get(f"{BASE_URL}/mgmt/tm/ltm/pool", auth=auth)
        print(f"✅ Status: {response.status_code} (esperado: 200)")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_create_pool():
    """Teste de criação de pool com autenticação"""
    print("\n🔍 Testando criação de pool...")
    try:
        auth = HTTPBasicAuth(USERNAME, PASSWORD)
        pool_data = {
            "name": "test-pool",
            "loadBalancingMode": "round-robin",
            "description": "Pool de teste criado via API"
        }
        response = requests.post(
            f"{BASE_URL}/mgmt/tm/ltm/pool", 
            json=pool_data,
            auth=auth
        )
        print(f"✅ Status: {response.status_code} (esperado: 201)")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_health_endpoint():
    """Teste do endpoint de saúde (sem autenticação)"""
    print("\n🔍 Testando endpoint de saúde...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando testes de autenticação do F5 Simulator")
    print(f"📡 Servidor: {BASE_URL}")
    print(f"👤 Credenciais: {USERNAME}:{PASSWORD}")
    print("=" * 60)
    
    # Primeiro teste endpoint de saúde
    test_health_endpoint()
    
    # Testes de autenticação
    test_without_auth()
    test_wrong_credentials()
    test_correct_credentials()
    test_create_pool()
    
    print("\n" + "=" * 60)
    print("✅ Testes concluídos!")