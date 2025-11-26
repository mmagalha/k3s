# Makefile para gerenciar Redis deployment

NAMESPACE ?= superset
REDIS_PASSWORD ?= redis-superset-password

.PHONY: help deploy status logs test clean backup restore

help: ## Mostra esta ajuda
	@echo "Redis Deployment Manager"
	@echo "========================"
	@echo "Comandos disponíveis:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

deploy: ## Implanta o Redis no Kubernetes
	@echo "🚀 Deploying Redis..."
	kubectl apply -f redis-deploy.yaml
	@echo "✅ Redis deployment applied"
	@echo "⏳ Waiting for Redis to be ready..."
	kubectl wait --for=condition=ready pod -l app=redis -n $(NAMESPACE) --timeout=300s
	@echo "✅ Redis is ready!"

status: ## Verifica o status do Redis
	@echo "📊 Redis Status"
	@echo "==============="
	@echo "Pods:"
	kubectl get pods -n $(NAMESPACE) -l app=redis
	@echo ""
	@echo "Services:"
	kubectl get svc -n $(NAMESPACE) -l app=redis
	@echo ""
	@echo "PVC:"
	kubectl get pvc -n $(NAMESPACE) redis-data
	@echo ""
	@echo "ConfigMap:"
	kubectl get configmap -n $(NAMESPACE) redis-config

logs: ## Mostra os logs do Redis
	kubectl logs -n $(NAMESPACE) deployment/redis -f

test: ## Testa a conectividade do Redis
	@echo "🧪 Testing Redis connectivity..."
	kubectl exec -n $(NAMESPACE) deployment/redis -- redis-cli -a $(REDIS_PASSWORD) ping
	@echo "✅ Redis is responding to ping"
	kubectl exec -n $(NAMESPACE) deployment/redis -- redis-cli -a $(REDIS_PASSWORD) info replication
	@echo "✅ Redis test completed"

shell: ## Conecta ao shell do Redis
	kubectl exec -it -n $(NAMESPACE) deployment/redis -- sh

redis-cli: ## Conecta ao Redis CLI
	kubectl exec -it -n $(NAMESPACE) deployment/redis -- redis-cli -a $(REDIS_PASSWORD)

info: ## Mostra informações do Redis
	kubectl exec -n $(NAMESPACE) deployment/redis -- redis-cli -a $(REDIS_PASSWORD) info

backup: ## Faz backup dos dados do Redis
	@echo "💾 Creating Redis backup..."
	kubectl exec -n $(NAMESPACE) deployment/redis -- redis-cli -a $(REDIS_PASSWORD) BGSAVE
	@echo "✅ Background save initiated"
	@echo "📁 To download backup file:"
	@echo "kubectl cp $(NAMESPACE)/$$(kubectl get pod -n $(NAMESPACE) -l app=redis -o jsonpath='{.items[0].metadata.name}'):/data/dump.rdb ./redis-backup-$$(date +%Y%m%d-%H%M%S).rdb"

clean: ## Remove o deployment do Redis (CUIDADO: Remove dados!)
	@echo "⚠️  WARNING: This will delete Redis and ALL DATA!"
	@echo "Press Ctrl+C to cancel, or wait 10 seconds to continue..."
	@sleep 10
	kubectl delete -f redis-deploy.yaml
	@echo "🗑️  Redis deployment removed"

restart: ## Reinicia o deployment do Redis
	@echo "🔄 Restarting Redis deployment..."
	kubectl rollout restart deployment/redis -n $(NAMESPACE)
	kubectl rollout status deployment/redis -n $(NAMESPACE)
	@echo "✅ Redis restarted"

scale-up: ## Escala o Redis para 1 replica (padrão)
	kubectl scale deployment redis --replicas=1 -n $(NAMESPACE)

scale-down: ## Para o Redis (0 replicas)
	kubectl scale deployment redis --replicas=0 -n $(NAMESPACE)

update-config: ## Atualiza configuração do Redis
	kubectl create configmap redis-config --from-file=redis.conf --dry-run=client -o yaml | kubectl apply -n $(NAMESPACE) -f -
	$(MAKE) restart

monitor: ## Mostra uso de recursos em tempo real
	watch kubectl top pod -n $(NAMESPACE) -l app=redis

network-test: ## Testa conectividade de rede do Redis
	@echo "🌐 Testing network connectivity..."
	kubectl run redis-test --rm -i --tty --image=redis:alpine -- redis-cli -h redis.$(NAMESPACE).svc.cluster.local -p 6379 -a $(REDIS_PASSWORD) ping

describe: ## Mostra detalhes do deployment
	kubectl describe deployment redis -n $(NAMESPACE)
	kubectl describe pod -l app=redis -n $(NAMESPACE)

events: ## Mostra eventos relacionados ao Redis
	kubectl get events -n $(NAMESPACE) --field-selector involvedObject.name=redis

# Comandos avançados
port-forward: ## Faz port-forward do Redis para acesso local
	@echo "🔗 Port forwarding Redis to localhost:6379"
	@echo "Use redis-cli -p 6379 -a $(REDIS_PASSWORD) para conectar"
	kubectl port-forward -n $(NAMESPACE) service/redis 6379:6379

debug: ## Inicia pod de debug para troubleshooting
	kubectl run redis-debug --rm -i --tty --image=redis:alpine -- sh

# Utilitários
check-namespace: ## Verifica se o namespace existe
	@kubectl get namespace $(NAMESPACE) >/dev/null 2>&1 || (echo "❌ Namespace $(NAMESPACE) não existe" && exit 1)

create-namespace: ## Cria o namespace se não existir
	kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -

# Default target
all: deploy status test