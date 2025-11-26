# Makefile para o projeto phpipam
# Autor: Marcos Magalhães
# Data: 2024-10-01
# Descrição: Este Makefile automatiza tarefas comuns para o projeto phpipam.
# Uso: Execute 'make <tarefa>' para executar uma tarefa específica.
# Exemplo: 'make build' para construir a imagem Docker.
# Variáveis
IMAGE_NAME ?= reg.mmagalha.com/phpipam/phpipam
TAG        ?= v0.0.4
DOCKERFILE ?= Dockerfile
CONTEXT    ?= .
# Configurações do banco de dados (ajuste conforme necessário)
DB_HOST    ?= 172.31.254.120
DB_PORT    ?= 5432
DB_NAME    ?= finops
DB_USER    ?= phpipam
DB_PASS    ?= 'J/[lSUAHw>sGWFX2'
PARALLEL_MODE ?= true
MAX_WORKERS ?= 10
BATCH_SIZE ?= 20
CHUNK_SIZE ?= 50000
# use make build IMAGE_NAME=myimage TAG=v1.0
# Tarefas
.PHONY: build push deploy all
build:
	docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) -f $(DOCKERFILE) $(CONTEXT)
push:
	docker push $(IMAGE_NAME):$(TAG)
deploy:
	kubectl apply -k .
	kubectl set image deployment/phpipam phpipam=$(IMAGE_NAME):$(TAG) -n phpipam
run:
	docker run -it \
	  -e DB_HOST=$(DB_HOST) \
	  -e DB_PORT=$(DB_PORT) \
	  -e DB_NAME=$(DB_NAME) \
	  -e DB_USER=$(DB_USER) \
	  -e DB_PASS=$(DB_PASS) \
	  -e PARALLEL_MODE=$(PARALLEL_MODE) \
	  -e MAX_WORKERS=$(MAX_WORKERS) \
	  -e BATCH_SIZE=$(BATCH_SIZE) \
	  -e CHUNK_SIZE=$(CHUNK_SIZE) \
	  -v ./data:/data \
	  -v ./processed:/processed \
	  -v ./errors:/errors \
	  $(IMAGE_NAME):$(TAG)
localrun:
	python3 -m venv .venv 
	. .venv/bin/activate && \
	pip install --no-cache-dir -r app/requirements.txt
	export DB_HOST=$(DB_HOST) && \
	export DB_PORT=$(DB_PORT) && \
	export DB_NAME=$(DB_NAME) && \
	export DB_USER=$(DB_USER) && \
	export DB_PASS=$(DB_PASS) && \
	export PARALLEL_MODE=$(PARALLEL_MODE) && \
	export MAX_WORKERS=$(MAX_WORKERS) && \
	export BATCH_SIZE=$(BATCH_SIZE) && \
	export CHUNK_SIZE=$(CHUNK_SIZE) && \
	python3 app/import.py

all: build push deploy
# Fim do Makefile