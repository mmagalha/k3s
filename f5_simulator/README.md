# F5 Simulator com Autenticação Básica

## Visão Geral

O F5 Simulator agora inclui autenticação HTTP Basic para simular melhor o comportamento real da API F5 BIG-IP.

## Configuração de Credenciais

### Credenciais Padrão
- **Username**: `admin`
- **Password**: `admin`

### Personalizar Credenciais

Você pode personalizar as credenciais usando variáveis de ambiente:

```bash
export F5_USERNAME=meuusuario
export F5_PASSWORD=minhasenha
python3 f5_simulator.py
```

## Como Usar

### 1. Iniciando o Servidor

```bash
# Com credenciais padrão
python3 f5_simulator.py

# Com credenciais personalizadas
F5_USERNAME=admin F5_PASSWORD=f5admin python3 f5_simulator.py
```

### 2. Fazendo Requisições com Autenticação

#### Usando curl
```bash
# Listar pools
curl -u admin:admin http://localhost:8080/mgmt/tm/ltm/pool

# Criar um pool
curl -u admin:admin -X POST \
  -H "Content-Type: application/json" \
  -d '{"name": "web-pool", "loadBalancingMode": "round-robin"}' \
  http://localhost:8080/mgmt/tm/ltm/pool
```

#### Usando Python requests
```python
import requests
from requests.auth import HTTPBasicAuth

auth = HTTPBasicAuth('admin', 'admin')

# Listar pools
response = requests.get('http://localhost:8080/mgmt/tm/ltm/pool', auth=auth)
print(response.json())

# Criar pool
pool_data = {
    "name": "web-pool",
    "loadBalancingMode": "round-robin"
}
response = requests.post(
    'http://localhost:8080/mgmt/tm/ltm/pool', 
    json=pool_data, 
    auth=auth
)
```

#### Configuração para Ansible F5 Collection

No seu inventory ou playbook Ansible:

```yaml
---
- hosts: f5
  vars:
    f5_host: localhost
    f5_port: 8080
    f5_username: admin
    f5_password: admin
    f5_validate_certs: false
  tasks:
    - name: Create pool
      f5networks.f5_modules.bigip_pool:
        provider:
          server: "{{ f5_host }}"
          server_port: "{{ f5_port }}"
          user: "{{ f5_username }}"
          password: "{{ f5_password }}"
          validate_certs: "{{ f5_validate_certs }}"
        name: web-pool
        lb_method: round_robin
```

## Endpoints Disponíveis

Todos os endpoints agora requerem autenticação básica, exceto:
- `GET /` - Endpoint de saúde (mostra informações de autenticação)

### Endpoints Protegidos
- `GET /mgmt/tm/ltm/pool` - Listar pools
- `POST /mgmt/tm/ltm/pool` - Criar pool
- `GET /mgmt/tm/ltm/pool/{id}` - Obter pool
- `PUT/PATCH /mgmt/tm/ltm/pool/{id}` - Atualizar pool
- `DELETE /mgmt/tm/ltm/pool/{id}` - Deletar pool
- E todos os endpoints de members e virtuals...

## Testando a Autenticação

Execute o script de teste incluído:

```bash
# Instale requests se necessário
pip3 install requests

# Execute os testes
python3 test_auth.py
```

## Respostas de Erro

### Sem Autenticação (401)
```json
{
  "detail": "Invalid credentials"
}
```

### Credenciais Incorretas (401)
```json
{
  "detail": "Invalid credentials"
}
```

## Logs de Segurança

O simulador registra tentativas de autenticação:
- ✅ Autenticações bem-sucedidas são registradas em nível DEBUG
- ❌ Falhas de autenticação são registradas em nível WARNING

Verifique o arquivo `f5_simulator.log` para auditoria de segurança.

## Integração com LTM Operator

Para usar com o LTM Operator, configure as credenciais nos Secrets do Kubernetes:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: f5-credentials
type: Opaque
stringData:
  username: admin
  password: admin
  host: f5-simulator.default.svc.cluster.local
  port: "8080"
```