# Redis Deployment para Superset

Este diretório contém os manifestos Kubernetes para deployment do Redis como cache para o Apache Superset.

## 📋 Recursos Incluídos

### Recursos Principais
- **Namespace**: `superset` para organização
- **ConfigMap**: Configuração otimizada do Redis
- **Secret**: Credenciais seguras do Redis
- **PersistentVolumeClaim**: Armazenamento persistente (2Gi)
- **Deployment**: Redis 7.2 Alpine com configurações de produção
- **Service**: Exposição interna do Redis

### Recursos Opcionais
- **ServiceMonitor**: Para monitoramento com Prometheus
- **NetworkPolicy**: Políticas de rede para segurança
- **PodDisruptionBudget**: Para alta disponibilidade

## 🚀 Como Implantar

### Pré-requisitos
- Cluster Kubernetes funcionando
- `kubectl` configurado
- StorageClass disponível para PVCs

### Deployment
```bash
# Aplicar todos os manifestos
kubectl apply -f redis-deploy.yaml

# Verificar status
kubectl get pods -n superset -l app=redis
kubectl get svc -n superset -l app=redis
kubectl get pvc -n superset
```

### Verificar Funcionamento
```bash
# Conectar ao Redis para teste
kubectl exec -it -n superset deployment/redis -- redis-cli -a redis-superset-password ping

# Ver logs
kubectl logs -n superset deployment/redis -f
```

## 🔧 Configuração

### Credenciais
- **Senha padrão**: `redis-superset-password`
- **⚠️ IMPORTANTE**: Altere a senha em produção no Secret `redis-secret`

### Recursos Computacionais
- **Requests**: 128Mi RAM, 100m CPU
- **Limits**: 512Mi RAM, 500m CPU
- **Armazenamento**: 2Gi persistente

### Configuração do Redis
O Redis está configurado com:
- Persistência RDB e AOF habilitada
- Política de memória: `allkeys-lru`
- Limite de memória: 256MB
- Autenticação por senha
- Bind em todas as interfaces

## 🔗 Integração com Superset

Para conectar o Superset ao Redis, use:

```python
# Variável de ambiente no Superset
REDIS_URL = "redis://:redis-superset-password@redis:6379/0"

# Ou no arquivo de configuração
CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'superset_',
    'CACHE_REDIS_HOST': 'redis',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_PASSWORD': 'redis-superset-password',
    'CACHE_REDIS_DB': 0,
}
```

## 📊 Monitoramento

### Health Checks
- **Liveness Probe**: Verifica se o Redis responde
- **Readiness Probe**: Verifica se está pronto para receber tráfego

### Prometheus (Opcional)
Se você tem o Prometheus Operator instalado:
```bash
# O ServiceMonitor será automaticamente descoberto
kubectl get servicemonitor -n superset
```

### Métricas Importantes
- Uso de memória
- Número de conexões
- Taxa de hit/miss do cache
- Operações por segundo

## 🔒 Segurança

### Medidas Implementadas
- **Autenticação**: Senha obrigatória
- **NetworkPolicy**: Restringe tráfego de rede
- **SecurityContext**: Container roda como usuário não-root
- **Secrets**: Credenciais armazenadas de forma segura

### Recomendações Adicionais
1. **Mude a senha** no Secret antes do deployment em produção
2. **Configure TLS** se necessário para comunicação criptografada
3. **Implemente backup** dos dados Redis se crítico
4. **Monitore uso de recursos** regularmente

## 🛠️ Manutenção

### Backup Manual
```bash
# Salvar snapshot
kubectl exec -n superset deployment/redis -- redis-cli -a redis-superset-password BGSAVE

# Copiar dados para backup
kubectl cp superset/redis-pod:/data/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb
```

### Scaling
```bash
# Redis é single-instance por design
# Para alta disponibilidade, considere Redis Sentinel ou Cluster
```

### Atualizações
```bash
# Atualizar imagem
kubectl set image deployment/redis redis=redis:7.2-alpine -n superset

# Verificar rollout
kubectl rollout status deployment/redis -n superset
```

## ⚠️ Observações Importantes

1. **Single Instance**: Este deployment é para uma única instância do Redis
2. **Persistência**: Dados são salvos no PVC, mas considere backups regulares
3. **Memória**: Configurado com 256MB de limite, ajuste conforme necessário
4. **Rede**: Por padrão, apenas pods no namespace `superset` podem acessar

## 🔧 Customizações

### Alterar Configuração do Redis
Edite o ConfigMap `redis-config` e reinicie o deployment:
```bash
kubectl edit configmap redis-config -n superset
kubectl rollout restart deployment/redis -n superset
```

### Aumentar Recursos
Edite o Deployment e ajuste os recursos:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "200m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

### Habilitar SSL/TLS
1. Crie certificados
2. Monte como Secret
3. Atualize configuração do Redis
4. Atualize URL de conexão no Superset