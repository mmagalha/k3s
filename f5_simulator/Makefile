PKG_NAME   ?= 'reg.mmagalha.com/library/f5-simulator'
VERSION    ?= '0.0.2' 
BUNDlE_IMG ?= $(PKG_NAME):$(VERSION)
KUSTOMIZE  ?= $(shell which kustomize)
KUBECTL    ?= $(shell which kubectl)

build:
	docker buildx build . --push --tag $(BUNDlE_IMG)

deploy:
	$(KUSTOMIZE) edit set image f5-simulator=$(BUNDlE_IMG)
	$(KUSTOMIZE) build . | $(KUBECTL) apply -f -
	$(KUBECTL) rollout restart deployment f5-simulator -n f5-simulator

all: build deploy