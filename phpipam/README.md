# phpIPAM Deployment no Kubernetes

Este diretório contém os manifestos Kubernetes para deployment completo do phpIPAM, baseado na configuração docker-compose fornecida.

## 📋 Componentes Incluídos

### Recursos Principais
- **Namespace**: `phpipam` para organização
- **Secret**: Credenciais seguras do banco de dados
- **ConfigMap**: Configurações de ambiente
- **PersistentVolumeClaims**: Armazenamento persistente para:
  - Dados do MariaDB (10Gi)
  - Logos personalizados (1Gi)
  - Certificados CA (100Mi)

### Deployments
1. **MariaDB**: Banco de dados principal
2. **phpIPAM Web**: Interface web principal
3. **phpIPAM Cron**: Serviços de background e scanning

### Services
- **phpipam-mariadb**: Exposição interna do banco
- **phpipam-web**: Exposição da interface web
- **phpipam-mariadb-admin**: Service adicional para administração

### Recursos de Segurança
- **NetworkPolicy**: Controle de tráfego de rede
- **ServiceAccount**: Conta de serviço dedicada
- **RBAC**: Roles e bindings necessários
- **PodDisruptionBudget**: Alta disponibilidade

### Recursos Adicionais
- **Ingress**: Acesso externo via `phpipam.mmagalha.com`
- **HorizontalPodAutoscaler**: Auto-scaling baseado em CPU/Memory

## 🚀 Como Implantar

### Pré-requisitos
- Cluster Kubernetes funcionando
- Ingress Controller (NGINX) configurado
- Cert-manager configurado
- StorageClass disponível para PVCs

### Deployment Rápido
```bash
# Aplicar todos os manifestos
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Verificar status
kubectl get all -n phpipam
```

### Verificar Implantação
```bash
# Verificar pods
kubectl get pods -n phpipam

# Verificar services
kubectl get svc -n phpipam

# Verificar PVCs
kubectl get pvc -n phpipam

# Verificar ingress
kubectl get ingress -n phpipam
```

## 🔧 Configuração

### Credenciais Padrão
**⚠️ IMPORTANTE**: Altere as senhas antes do deployment em produção!

- **MySQL Root Password**: `secure_mysql_root_password_2024`
- **phpIPAM DB Password**: `secure_phpipam_db_password_2024`
- **MySQL User**: `phpipam`
- **MySQL Database**: `phpipam`

### Variáveis de Ambiente
```yaml
TZ: "Europe/Lisbon"
IPAM_DATABASE_HOST: "phpipam-mariadb"
IPAM_DATABASE_WEBHOST: "%"
SCAN_INTERVAL: "1h"
```

### Recursos Computacionais

#### MariaDB
- **Requests**: 512Mi RAM, 250m CPU
- **Limits**: 1Gi RAM, 500m CPU
- **Storage**: 10Gi persistente

#### phpIPAM Web
- **Requests**: 256Mi RAM, 100m CPU
- **Limits**: 512Mi RAM, 500m CPU
- **Capabilities**: NET_ADMIN, NET_RAW

#### phpIPAM Cron
- **Requests**: 128Mi RAM, 50m CPU
- **Limits**: 256Mi RAM, 200m CPU
- **Capabilities**: NET_ADMIN, NET_RAW

## 🔗 Acesso

### Interface Web
- **URL**: https://phpipam.mmagalha.com
- **Credenciais**: Configuradas durante a primeira execução

### Acesso ao Banco (Admin)
```bash
# Port-forward para acesso local
kubectl port-forward -n phpipam svc/phpipam-mariadb-admin 3306:3306

# Conectar com cliente MySQL
mysql -h localhost -P 3306 -u phpipam -p
```

## 📊 Monitoramento

### Health Checks
- **MariaDB**: mysqladmin ping
- **Web**: HTTP GET na porta 80
- **Cron**: Processo ativo

### Logs
```bash
# Logs do MariaDB
kubectl logs -n phpipam deployment/phpipam-mariadb -f

# Logs do Web
kubectl logs -n phpipam deployment/phpipam-web -f

# Logs do Cron
kubectl logs -n phpipam deployment/phpipam-cron -f
```

### Auto-scaling
O phpIPAM Web está configurado com HPA:
- **Min Replicas**: 1
- **Max Replicas**: 3
- **CPU Target**: 70%
- **Memory Target**: 80%

## 🔒 Segurança

### Medidas Implementadas
1. **Secrets**: Credenciais armazenadas de forma segura
2. **NetworkPolicy**: Restringe comunicação entre pods
3. **RBAC**: Permissões mínimas necessárias
4. **Security Context**: Capabilities específicas apenas onde necessário
5. **TLS**: Certificado automático via cert-manager

### Capabilities Especiais
Os containers do phpIPAM Web e Cron precisam das capabilities:
- **NET_ADMIN**: Para gerenciar interfaces de rede
- **NET_RAW**: Para enviar/receber pacotes RAW (pings, SNMP)

## 🛠️ Manutenção

### Backup do Banco
```bash
# Criar backup
kubectl exec -n phpipam deployment/phpipam-mariadb -- \
  mysqldump -u root -p$MYSQL_ROOT_PASSWORD phpipam > phpipam-backup.sql

# Restaurar backup
kubectl exec -i -n phpipam deployment/phpipam-mariadb -- \
  mysql -u root -p$MYSQL_ROOT_PASSWORD phpipam < phpipam-backup.sql
```

### Atualizações
```bash
# Atualizar imagens
kubectl set image deployment/phpipam-web phpipam-web=phpipam/phpipam-www:latest -n phpipam
kubectl set image deployment/phpipam-cron phpipam-cron=phpipam/phpipam-cron:latest -n phpipam

# Verificar rollout
kubectl rollout status deployment/phpipam-web -n phpipam
kubectl rollout status deployment/phpipam-cron -n phpipam
```

### Scaling Manual
```bash
# Escalar Web
kubectl scale deployment phpipam-web --replicas=2 -n phpipam

# Verificar status
kubectl get deployment phpipam-web -n phpipam
```

## 🔧 Customizações

### Alterar Configurações
1. Edite o ConfigMap:
   ```bash
   kubectl edit configmap phpipam-config -n phpipam
   ```

2. Reinicie os deployments:
   ```bash
   kubectl rollout restart deployment/phpipam-web -n phpipam
   kubectl rollout restart deployment/phpipam-cron -n phpipam
   ```

### Alterar Senhas
1. Edite o Secret:
   ```bash
   kubectl edit secret phpipam-secrets -n phpipam
   ```

2. Reinicie todos os deployments:
   ```bash
   kubectl rollout restart deployment/phpipam-mariadb -n phpipam
   kubectl rollout restart deployment/phpipam-web -n phpipam
   kubectl rollout restart deployment/phpipam-cron -n phpipam
   ```

### Alterar Domínio
1. Edite o Ingress:
   ```bash
   kubectl edit ingress phpipam-ingress -n phpipam
   ```

2. Atualize o host e TLS conforme necessário.

## ⚠️ Observações Importantes

1. **Primeira Execução**: phpIPAM pode demorar alguns minutos para inicializar na primeira vez
2. **Persistência**: Dados são salvos em PVCs, mas faça backups regulares
3. **Capabilities**: NET_ADMIN/NET_RAW são necessárias para funcionalidades de rede
4. **Single Database**: MariaDB roda em modo single-instance
5. **Scaling**: Apenas o componente Web pode ser escalado horizontalmente

## 🔗 Referências

- [phpIPAM Official Documentation](https://phpipam.net/documents/)
- [phpIPAM Docker Images](https://hub.docker.com/u/phpipam)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

## 📞 Suporte

Para problemas específicos do deployment:
1. Verifique os logs dos pods
2. Confirme se todos os PVCs foram criados
3. Verifique se o ingress está funcionando
4. Teste conectividade com o banco de dados