# Política de Validação de Annotation Partition para Recursos LTM

Esta política do Gatekeeper valida se recursos LTM da Sonae possuem a annotation `partition` com valores permitidos.

## Arquivos

- `k8spartitionannotations-template.yaml` - ConstraintTemplate que define a política
- `partition-constraint.yaml` - Constraint que aplica a política aos recursos LTM
- `test-examples.yaml` - Exemplos de recursos LTM para teste

## Recursos Alvo

A política aplica-se exclusivamente aos seguintes Custom Resources:
- **LTMPoolMember** (`ltmpoolmembers.ltm.network.sonae.pt`)
- **LTMPool** (`ltmpools.ltm.network.sonae.pt`)
- **LTMVirtual** (`ltmvirtuals.ltm.network.sonae.pt`)

## Como Funciona

### ConstraintTemplate
Define uma política Rego que:
1. **Verifica existência** da annotation `metadata.annotations.partition`
2. **Valida valores** contra uma lista de valores permitidos
3. **Isenta namespaces** específicos da validação
4. **Fornece mensagens** de erro detalhadas

### Parâmetros Configuráveis
- `allowedPartitions`: Lista de valores permitidos (ex: ["PP", "TST", "DEV"])
- `exemptNamespaces`: Namespaces isentos da validação

## Instalação

1. **Instalar o ConstraintTemplate:**
   ```bash
   kubectl apply -f k8spartitionannotations-template.yaml
   ```

2. **Aplicar o Constraint:**
   ```bash
   kubectl apply -f partition-constraint.yaml
   ```

3. **Verificar instalação:**
   ```bash
   kubectl get constrainttemplate
   kubectl get k8spartitionannotations
   ```

## Testes

### Recursos Válidos ✅
```yaml
# LTMPool com partition válida
apiVersion: ltm.network.sonae.pt/v1alpha1
kind: LTMPool
metadata:
  annotations:
    partition: "PP"    # Valor permitido
```

```yaml
# LTMVirtual com partition válida
apiVersion: ltm.network.sonae.pt/v1alpha1
kind: LTMVirtual
metadata:
  annotations:
    partition: "TST"   # Valor permitido
```

### Recursos Inválidos ❌
```yaml
# LTMPoolMember com partition inválida
apiVersion: ltm.network.sonae.pt/v1alpha1
kind: LTMPoolMember
metadata:
  annotations:
    partition: "INVALID"  # Valor não permitido
```

```yaml
# LTMPool sem annotation partition
apiVersion: ltm.network.sonae.pt/v1alpha1
kind: LTMPool
metadata:
  # Sem annotation partition - obrigatória
```

### Testar Exemplos
```bash
# Tentar aplicar recursos de teste (alguns falharão)
kubectl apply -f test-examples.yaml
```

## Mensagens de Erro

### Annotation Ausente
```
Annotation 'partition' é obrigatória
```

### Valor Inválido
```
Valor de partition 'INVALID' não é permitido. Valores permitidos: ["PP", "TST", "DEV"]
```

## Customização

### Alterar Valores Permitidos
Edite `partition-constraint.yaml`:
```yaml
parameters:
  allowedPartitions: ["PROD", "STAGING", "DEV"]
```

### Adicionar Namespaces Isentos
```yaml
parameters:
  exemptNamespaces: 
    - "kube-system"
    - "monitoring"
    - "logging"
```

### Aplicar a Recursos Específicos
A política já está configurada para recursos LTM. Para modificar:
```yaml
spec:
  match:
    kinds:
      - apiGroups: ["ltm.network.sonae.pt"]
        kinds: ["LTMPool"]  # Apenas LTMPools
```

## Verificação de Violations

```bash
# Ver violações ativas
kubectl get k8spartitionannotations require-partition-annotation -o yaml

# Ver detalhes das violações
kubectl describe k8spartitionannotations require-partition-annotation

# Ver recursos LTM no cluster
kubectl get ltmpools,ltmvirtuals,ltmpoolmembers --all-namespaces
```

## Monitoramento

As violações aparecem em:
- Events do Kubernetes
- Status do constraint
- Logs do Gatekeeper controller

```bash
# Ver eventos relacionados
kubectl get events --field-selector reason=ConstraintViolation

# Ver status do constraint
kubectl get k8spartitionannotations -o jsonpath='{.items[0].status}'
```