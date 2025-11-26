# Manual de ajustes do K3S para ambiente de desenvolvimento de operadores

De forma a facilitar o processo de deploy de uma estrutura k3s standalone para desenvolvimento, descrevo abaixo os passos necessários para configurar: 

1. K3S
2. Ingress Gateway
3. Certmanager e keycloak
4. Autenticação do K3S no keycloak 

Desta forma, conseguimos ter um ambiente com todos os recursos necessários para o desenvolvimento de Operadores K8S com autenticação externa baseada e OIDC

## 1. Instalação do K3S

Para instalar o k3s seguimos o modelo de instalação padrão do k3s, usando o script disponibilizado pelo desenvolvedor.

```bash
$ curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable=traefik" sh -
```
Usamos a opção INSTALL_K3S_EXEC="--disable=traefik" pois pretendemos usar o nginx como Ingress Gateway.

Depois de instalado precisamos criar um arquivo de configuração para o k3s em /etc/rancher/k3s/config.yaml

```yaml
# Informa ao API Server onde conseguir os tokens de autenticação dos usuários;

kube-apiserver-arg:
  - "oidc-issuer-url=https://key.example.com/realms/master"
  - "oidc-client-id=k3s-cluster"
  - "oidc-username-claim=preferred_username"
  - "oidc-groups-claim=groups"

# Muda a máscara de criação do kubeconfg em /etc/rancher/k3s/k3s.yaml permitindo que o usuário tenha acesso as configurações **Atenção: APENAS PARA USO EM AMBIENTE DE DESENVOLVIMENTO**
write-kubeconfig-mode: "0644"
# Mantem o traefik desabilitado
disable: traefik  
``` 

## 2. Nginx Ingress Gateway

Vamos usar o helm para fazer o deploy do Nginx, seguindo a documentação oficial. Esse comando irá criar o namespace e instalar o ingress Gateway

```bash
$ helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace
```

## 3. Certmanager e keycloak
Neste repositório temos os manifestos necessários para instalação e configuração do cert-manager e do keycloak

Estrutura de diretórios do projeto
``` bash
.
├── certmanager
│   ├── certificate.yaml
│   ├── cert-manager.yaml
│   ├── cloudflaresecret.yaml
│   ├── clusterissue.yaml
│   └── kustomization.yaml
├── keycloak
│   ├── ingress.yaml
│   ├── keycloak.yaml
│   ├── kustomization.yaml
│   ├── rbac_cluster-admin.yaml
│   ├── rbac_group-admin.yaml
│   └── rbac_infra-core-cloud.yaml
├── kustomization.yaml
└── README.md
```
Para instalação dos itens acima basta fazer:
```bash
$ kubectl apply -k .
```

Boa! Vou estruturar a documentação completa para você, baseada em tudo que revisamos. Ela cobre desde a preparação no **Keycloak**, ajustes no **K3s**, até a configuração do **kubectl**.

---

## 4.Autenticação do K3s com Keycloak via OIDC

### 1. Pré-requisitos

* Cluster **K3s** instalado e em execução.
* Acesso ao **Keycloak** (>= 26.3.3).
* `kubectl` e `kubelogin` instalados na máquina cliente.

#### Instalando o kubelogin
```bash
curl -LO https://github.com/int128/kubelogin/releases/latest/download/kubelogin_linux_amd64.zip
unzip kubelogin_linux_amd64.zip -d /usr/local/bin
chmod +x /usr/local/bin/kubelogin
```
---

### 2. Configuração no Keycloak

1. Acesse o **Keycloak Admin Console**.
   Exemplo: `https://key.example.com/admin`.

2. Selecione o **Realm** (ex.: `master`).

3. Crie um **Client** para o Kubernetes:

   * **Client ID:** `k3s-cluster`
   * **Client type:** `OpenID Connect`
   * **Access Type:** `confidential` (ou `public`, se preferir sem client secret).
   * **Valid Redirect URIs:** `http://localhost/*` (necessário para o `kubelogin`).
   * **Web Origins:** `*` (ou restrito conforme necessidade).
   * **Service Accounts Enabled:** `ON`.

4. Configure **Client Scopes**:

   * `profile`, `email`, `groups`, `openid`.
   * Garanta que o `groups` está no **token scope**.

    Garantir profile e email como Default Client Scopes

    1. Vá em Clients → (seu cliente) → Client Scopes.

    2. Em Default Client Scopes, confirme a presença de profile e email.

        * Se não estiverem, Add client scope → profile e email (Assigned type: Default).
    (São built-ins do OIDC em Keycloak e já vêm com os mappers corretos.) 

        Observação: openid não é um client scope editável; é um meta-scope obrigatório do OIDC. Você não precisa (nem consegue) “criar” openid.

    3. Criar um client scope chamado groups

        Você vai expor a filiação a Groups do Keycloak na claim groups (que o Kubernetes lê por padrão quando você configura --oidc-groups-claim=groups).

        1. Client Scopes → Create

            * Name: groups
            * Protocol: openid-connect
            * Save.

        2. Aba Mappers → Create:

            * Mapper Type: Group Membership
            * (é o protocol mapper que emite a lista de grupos do usuário) 
            * Keycloak
            * Name: groups
            * Token Claim Name: groups
            * Add to ID token: ON
            * Add to access token: ON
            * Add to userinfo: ON
            * Full group path: OFF (assim evita barras como /team/dev; o Kubernetes prefere nomes simples).
            * Save.

        (Opcional, mas útil) Em Client Scopes → groups → Settings, ligue Include in token scope = ON (o nome groups aparecerá no scope do token quando solicitado). 

        ```text
        Nota: existe também o client scope microprofile-jwt, que mapeia “groups” como roles (padrão MicroProfile). Isso não é a mesma coisa que Keycloak Groups. Para RBAC do Kubernetes, o caminho mais direto é usar Group Membership emitindo a claim groups.   
        ```
    4. Ligar o scope groups ao seu cliente

        * **Clients → (seu cliente) → Client Scopes → Add client scope.**
        * Selecione groups e defina Assigned type como:
            * **Optional** → você precisa pedir groups no scope (como o kubelogin faz), ou
            * **Default** → sempre presente, mesmo sem pedir. (Optional só é aplicado quando o parâmetro scope inclui groups.) 
        
    5) Validar com o “Evaluate”

        Para ver o token já no formato final:
    
    * **Clients → (seu cliente) → Client Scopes → Evaluate**.
    * Escolha um usuário de teste e marque o optional `groups`.
    * Veja o ID Token e/ou Access Token gerado; confirme a claim  `"groups": ["grupoA","grupoB", ...].`


5. Atribua **Grupos e Roles** aos usuários:

   * Exemplo: usuário `example` pertence ao grupo `admin` e `default-roles-master`.
   * Esses grupos aparecerão no claim `groups` do JWT.
    
        Veja `Autorização via RBAC no Kubernetes`

---

## 3. Configuração no K3s

Edite o arquivo `/etc/rancher/k3s/config.yaml`:

```yaml
# /etc/rancher/k3s/config.yaml

https-listen-port: 6443

kube-apiserver-arg:
  - "oidc-issuer-url=https://key.example.com/realms/master"
  - "oidc-client-id=k3s-cluster"
  - "oidc-username-claim=preferred_username"
  - "oidc-groups-claim=groups"
  - "oidc-username-prefix="
  - "oidc-groups-prefix="
  # Necessário se Keycloak usar certificado custom:
  # - "oidc-ca-file=/var/lib/rancher/k3s/server/tls/ca.crt"
```

Reinicie o K3s:

```bash
sudo systemctl restart k3s
```

Confirme que os parâmetros foram aplicados:

```bash
ps aux | grep kube-apiserver | grep oidc
```

---

## 4. Configuração no kubectl

1. Teste a autenticação manual com `kubelogin`:

```bash
kubelogin get-token \
  --oidc-issuer-url=https://key.example.com/realms/master \
  --oidc-client-id=k3s-cluster \
  --oidc-extra-scope=openid \
  --oidc-extra-scope=profile \
  --oidc-extra-scope=email \
  --oidc-extra-scope=groups
```

Se funcionar, você receberá um token JWT válido.

2. Configure o `kubeconfig` para usar OIDC:

Edite o arquivo `~/.kube/config`:

```yaml
apiVersion: v1
clusters:
- cluster:
    server: https://127.0.0.1:6443
    certificate-authority-data: <CERTIFICADO_CA>
  name: k3s

users:
- name: example
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1
      command: kubelogin
      args:
      - get-token
      - --oidc-issuer-url=https://key.example.com/realms/master
      - --oidc-client-id=k3s-cluster
      - --oidc-extra-scope=openid
      - --oidc-extra-scope=profile
      - --oidc-extra-scope=email
      - --oidc-extra-scope=groups
      interactiveMode: IfAvailable
      provideClusterInfo: false

contexts:
- name: keycloak-context
  context:
    cluster: k3s
    user: example

current-context: keycloak-context
```

3. Valide a autenticação:

```bash
kubectl get ns
```

Se tudo estiver correto, você verá a lista de namespaces.

---

## 5. Autorização via RBAC no Kubernetes

O OIDC só faz **autenticação**. Para **autorizar**, crie regras RBAC com base nos grupos do Keycloak.

Exemplo: conceder permissões de admin para membros do grupo `admin`.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-binding
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: Group
  name: "admin"   # Nome do grupo que vem do Keycloak
  apiGroup: rbac.authorization.k8s.io
```

---

## 6. Testando o fluxo

1. Faça login pelo `kubelogin`:

   ```bash
   kubectl get pods -n kube-system
   ```

   → Se autorizado, verá os pods.

2. Teste com usuário sem grupo autorizado:

   ```bash
   kubectl get pods
   ```

   → Deve retornar erro de `Forbidden`.



# Troubleshooting

* **Erro:** `the server has asked for the client to provide credentials`
  → Verifique se o `kubeconfig` usa `exec: kubelogin` e não `--token` fixo.

* **Erro:** `invalid issuer`
  → Confira se o `oidc-issuer-url` no `config.yaml` bate exatamente com o do token (`iss` claim).

* **Erro de certificado**
  → Adicione `oidc-ca-file` apontando para o CA do Keycloak.

### Criar secret para registry privado

kubectl -n ltm-operator-system create secret docker-registry regcred \
  --docker-server=https://reg.mmagalha.com \
  --docker-username=mmagalha \
  --docker-password='ZHWyfehb3X!' \
  --docker-email=mmagalha@gmail.com
