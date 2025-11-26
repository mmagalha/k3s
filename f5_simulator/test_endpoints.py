#!/usr/bin/env python3
"""
Script de teste para verificar se os novos endpoints funcionam
seguindo o modelo oficial F5
"""
import requests
import json
import sys

# Configuração do servidor (assumindo que está rodando)
BASE_URL = "http://localhost:8080"
USERNAME = "admin"
PASSWORD = "f5password"  # Atualizado para corresponder ao deployment

def test_login_endpoint():
    """Testa o endpoint de login"""
    print("🔐 Testando endpoint de login...")
    
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
        "loginProviderName": "tmos"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/mgmt/shared/authn/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Login endpoint funcionando!")
            data = response.json()
            token = data.get('token', {}).get('token', 'N/A')
            print(f"Token recebido: {token}")
            print(f"Username: {data.get('username')}")
            print(f"Timeout: {data.get('token', {}).get('timeout')} segundos")
            return token
        else:
            print(f"❌ Login falhou: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro ao testar login: {e}")
        return None

def test_token_authentication(token):
    """Testa autenticação por token"""
    if not token:
        print("\n⚠️ Pulando teste de token - nenhum token disponível")
        return False
        
    print(f"\n🔑 Testando autenticação por token...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/mgmt/tm/sys",
            headers={
                "Content-Type": "application/json",
                "X-F5-Auth-Token": token
            }
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Autenticação por token funcionando!")
            data = response.json()
            print(f"Kind: {data.get('kind', 'N/A')}")
            return True
        else:
            print(f"❌ Autenticação por token falhou: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar token auth: {e}")
        return False

def test_basic_auth_sys_endpoint():
    """Testa o endpoint de sistema com basic auth"""
    print("\n📊 Testando endpoint de sistema com Basic Auth...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/mgmt/tm/sys",
            auth=(USERNAME, PASSWORD),
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ System endpoint funcionando!")
            data = response.json()
            print(f"Kind: {data.get('kind', 'N/A')}")
            print(f"Items: {len(data.get('items', []))}")
            return True
        else:
            print(f"❌ System endpoint falhou: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar system: {e}")
        return False

def test_token_info_endpoint(token):
    """Testa o endpoint de informações do token"""
    if not token:
        print("\n⚠️ Pulando teste de info do token - nenhum token disponível")
        return False
        
    print(f"\n🔍 Testando endpoint de informações do token...")
    
    try:
        response = requests.get(f"{BASE_URL}/mgmt/shared/authz/tokens/{token}")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Token info endpoint funcionando!")
            data = response.json()
            print(f"Token: {data.get('token', 'N/A')}")
            print(f"Username: {data.get('userName', 'N/A')}")
            return True
        else:
            print(f"❌ Token info falhou: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar token info: {e}")
        return False

def test_root_endpoint():
    """Testa o endpoint raiz"""
    print("\n🏠 Testando endpoint raiz...")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Root endpoint funcionando!")
            data = response.json()
            print(f"Simulador OK: {data.get('ok', False)}")
            print(f"Credenciais padrão: {data.get('default_credentials', 'N/A')}")
            return True
        else:
            print(f"❌ Root endpoint falhou: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar root: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Iniciando testes dos endpoints do simulador F5...")
    print(f"🔧 Base URL: {BASE_URL}")
    print(f"👤 Credenciais: {USERNAME}:{PASSWORD}")
    
    results = []
    
    # Testa endpoint raiz primeiro
    results.append(test_root_endpoint())
    
    # Testa login e obtém token
    token = test_login_endpoint()
    results.append(token is not None)
    
    # Testa autenticação básica
    results.append(test_basic_auth_sys_endpoint())
    
    # Testa autenticação por token
    results.append(test_token_authentication(token))
    
    # Testa endpoint de informações do token
    results.append(test_token_info_endpoint(token))
    
    print("\n📋 Resumo dos testes:")
    if all(results):
        print("✅ Todos os testes passaram!")
        print("🎉 Simulador F5 está funcionando corretamente!")
        sys.exit(0)
    else:
        failed_count = results.count(False)
        print(f"❌ {failed_count} de {len(results)} testes falharam!")
        sys.exit(1)