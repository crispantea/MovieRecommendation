set dotenv-load
set shell := ["bash", "-euo", "pipefail", "-c", ': "${ENV?ENV is required, e.g. ENV=local just up}"; set -a; for e in $ENV; do . ".env.$e"; done; eval "$0"']

# --------------------------------------------------------------
# Variables
# --------------------------------------------------------------

# Env Files
global_env_file  := ".env"
local_env_file   := ".env.local"
kind_env_file    := ".env.kind"
cloud_env_file   := ".env.cloud"
secrets_env_file := ".env.secrets"

# Directories
services_dir := "services"
scripts_dir  := "scripts"
tf_dir       := "infra"
ansible_dir  := "ansible"
manifests_dir := "manifests"

tf_dev_dir := tf_dir + "/environments/dev"
tf_dev_auth_dir := tf_dev_dir + "/auth"

# --------------------------------------------------------------
# Exported Variables - needed across scripts
# --------------------------------------------------------------

export SERVICES_DIR  := services_dir
export SECRETS_FILE  := secrets_env_file
export MANIFESTD_DIR := manifests_dir

# ------------------------------------------------------------------------------------------------ #
# Global targets - used across scripts
# ------------------------------------------------------------------------------------------------ #

# Initialize secrets and hydrate keycloak templates
init:
    bash {{scripts_dir}}/bootstrap.sh

build:
    {{compose}} build --no-cache

destroy:
    rm -f {{secrets_env_file}} \
          {{services_dir}}/authorization/import/realm-export.json \
          {{manifests_dir}}/keycloak/base/realm-export.json

# ------------------------------------------------------------------------------------------------ #
# Local / Docker Compose Stack
# ------------------------------------------------------------------------------------------------ #

# This uses the variables defined in the env files provided and fills the required vars in the docker compose file
compose := "docker compose --env-file " + global_env_file + \
                         " --env-file " + local_env_file + \
                         " --env-file " + secrets_env_file + \
                         " -f " + services_dir + "/docker-compose.yml"

# Initialize Keycloak container and create required resources using terraform
local-init-keycloak:
    {{compose}} up -d --wait auth-service
    set -a; source {{secrets_env_file}}; set +a && \
    . {{scripts_dir}}/terraform/keycloak/export-input-vars.sh && \
    terraform -chdir={{tf_dev_auth_dir}} init -input=false && \
    terraform -chdir={{tf_dev_auth_dir}} apply -auto-approve

# Full stack startup
local-up: local-init-keycloak
    {{compose}} up -d --wait

# Manually trigger movie dataset seeding (respects USE_TEMPLATE_DB or falls back)
seed-movies:
    {{compose}} exec movies-service python seed_db.py

# Manually trigger movie seeding specifically with template dataset
seed-movies-template:
    {{compose}} exec movies-service python seed_db.py --clear --template

# Manually trigger movie bulk ingestion from full CSV dataset
seed-movies-csv:
    {{compose}} exec movies-service python seed_db.py --clear --csv


# Tear down all running containers
local-clean:
    {{compose}} down

# Full wipe (containers down + remove generated secrets)
local-destroy: local-clean destroy

# ------------------------------------------------------------------------------------------------ #
# Local Kubernetes / Kind Stack
# ------------------------------------------------------------------------------------------------ #
cluster_name := "cluster-psia2026"

kind-init:
    # Create kind cluster (if doesnt exist)
    kind get clusters | grep -qx "{{cluster_name}}" || kind create cluster --config="{{manifests_dir}}/kind-cluster.yaml" --name={{cluster_name}}

kind-load-images: kind-init
    kind load docker-image agi-frontend:latest --name={{cluster_name}}
    kind load docker-image agi-profiles-service:latest --name={{cluster_name}}
    kind load docker-image agi-inference-service:latest --name={{cluster_name}}

kind-deploy: kind-load-images
    # ---- Add required Helm repos and deploy Gateway API & kgateway CRDs ----
    # Add bitnami repo
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo update

    # Apply the Gateway API CRDs
    kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.1/standard-install.yaml

    # Apply kgateway specific CRDs that will be used to define the type of proxy that will be created
    helm upgrade -i kgateway-crds oci://cr.kgateway.dev/kgateway-dev/charts/kgateway-crds \
    -n kgateway-system \
    --create-namespace \
    --version 2.4.5 \
    --wait
    # ------------------------------------------------------------------------

    # -------------------------- Apply microservices -------------------------
    # Build and deploy the kgateway wrapper (already comes with the gateway definition)
    helm dependency build "{{manifests_dir}}/kgateway/base"
    helm upgrade -i kgateway "{{manifests_dir}}/kgateway/base" \
    -n kgateway-system \
    --create-namespace \
    --wait

    # Build and deploy the keyclaok wrapper (already comes with the httproute, secrets and configmap used on keycloak)
    helm dependency build "{{manifests_dir}}/keycloak/base"
    set -a; source {{secrets_env_file}}; set +a && \
    envsubst < "{{manifests_dir}}/keycloak/base/values.yaml" | \
    helm upgrade --install keycloak "{{manifests_dir}}/keycloak/base" \
    -n keycloak \
    --create-namespace \
    --wait \
    -f -

    # Initialize keycloak resources using terraform
    set -a; source {{secrets_env_file}}; set +a && \
    . {{scripts_dir}}/terraform/keycloak/export-input-vars.sh && \
    terraform -chdir={{tf_dev_auth_dir}} init -input=false && \
    terraform -chdir={{tf_dev_auth_dir}} apply -auto-approve

    # Build and deploy the profiles-service wrapper
    helm dependency build "{{manifests_dir}}/profiles-service/database"
    set -a; source {{secrets_env_file}}; set +a && \
    envsubst < "{{manifests_dir}}/profiles-service/database/values.yaml" | \
    helm upgrade --install postgresql "{{manifests_dir}}/profiles-service/database" \
    -n profiles-service \
    --create-namespace \
    --wait \
    -f -

    set -a; source {{secrets_env_file}}; set +a && \
    kubectl kustomize "{{manifests_dir}}/profiles-service/overlays/prod" | envsubst | kubectl apply -f - --wait

    # Deploy Inference Service
    kubectl kustomize --load-restrictor LoadRestrictionsNone "manifests/inference-service/overlays/prod" | envsubst | kubectl apply -f - --wait
    
    # Deploy Frontend
    kubectl kustomize "{{manifests_dir}}/frontend/overlays/prod" | envsubst | kubectl apply -f - --wait


kind-deploy-profiles-service:
    # Build and deploy the profiles-service wrapper
    helm dependency build "{{manifests_dir}}/profiles-service/database"
    set -a; source {{secrets_env_file}}; set +a && \
    envsubst < "{{manifests_dir}}/profiles-service/database/values.yaml" | \
    helm upgrade --install postgresql "{{manifests_dir}}/profiles-service/database" \
    -n profiles-service \
    --create-namespace \
    --wait \
    -f -
    
    set -a; source {{secrets_env_file}}; set +a && \
    kubectl kustomize "{{manifests_dir}}/profiles-service/overlays/prod" | envsubst | kubectl apply -f - --wait

kind-clean-profiles-service:
    helm uninstall postgresql
    kubectl kustomize "{{manifests_dir}}/profiles-service/overlays/prod" | envsubst | kubectl delete -f - --wait

kind-deploy-inference-service:
    kubectl kustomize --load-restrictor LoadRestrictionsNone "manifests/inference-service/overlays/prod" | envsubst

kind-clean-inference-service:
    kubectl kustomize --load-restrictor LoadRestrictionsNone "manifests/inference-service/overlays/prod" |  envsubst | kubectl delete -f - --wait

kind-deploy-frontend:
    kubectl kustomize "{{manifests_dir}}/frontend/overlays/prod" | envsubst | kubectl apply -f - --wait

kind-clean-frontend:
    kubectl kustomize "{{manifests_dir}}/frontend/overlays/prod" | envsubst | kubectl delete -f - --wait

kind-clean: 
    kind delete cluster --name={{cluster_name}}

kind-destroy: kind-clean destroy

# ------------------------------------------------------------------------------------------------ #
# Cloud Kubernetes / Production Stack
# ------------------------------------------------------------------------------------------------ #
tf_gcp_dir := tf_dir + "/gcp"

mgmt_cmd := "docker exec -it mgmt"
mgmt_project_dir := "/root/agi-project"
mgmt_tf_gcp_dir := mgmt_project_dir + "/" + tf_gcp_dir
mgmt_ansible_dir := mgmt_project_dir + "/" + ansible_dir

mgmt-up:
	docker build -t mgmt ./mgmt
	docker run --rm --name mgmt --hostname mgmt -v "$(pwd):{{mgmt_project_dir}}" -d mgmt

mgmt-down:
	docker stop mgmt

cloud-init target="":
    if [ "{{target}}" = "local" ]; then \
        terraform -chdir={{tf_gcp_dir}} init; \
    else \
        {{mgmt_cmd}} terraform -chdir={{mgmt_tf_gcp_dir}} init; \
    fi

cloud-plan target="":
    if [ "{{target}}" = "local" ]; then \
        terraform -chdir={{tf_gcp_dir}} plan; \
    else \
        {{mgmt_cmd}} terraform -chdir={{mgmt_tf_gcp_dir}} plan; \
    fi

cloud-apply target="":
    if [ "{{target}}" = "local" ]; then \
        terraform -chdir={{tf_gcp_dir}} apply; \
    else \
        {{mgmt_cmd}} terraform -chdir={{mgmt_tf_gcp_dir}} apply; \
    fi

cloud-ansible target="": cloud-apply
    if [ "{{target}}" = "local" ]; then \
        ANSIBLE_CONFIG="{{ansible_dir}}/ansible.cfg" ansible-playbook "{{ansible_dir}}/site.yml"; \
    else \
        {{mgmt_cmd}} env ANSIBLE_CONFIG="{{mgmt_ansible_dir}}/ansible.cfg" ansible-playbook "{{mgmt_ansible_dir}}/site.yml"; \
    fi

# TODO: Add k8s manifests
# cloud-deploy target="": cloud-apply cloud-ansible

cloud-output target="":
    if [ "{{target}}" = "local" ]; then \
        terraform -chdir={{tf_gcp_dir}} output; \
    else \
        {{mgmt_cmd}} terraform -chdir={{mgmt_tf_gcp_dir}} output; \
    fi

cloud-destroy target="":
    if [ "{{target}}" = "local" ]; then \
        terraform -chdir={{tf_gcp_dir}} destroy; \
    else \
        {{mgmt_cmd}} terraform -chdir={{mgmt_tf_gcp_dir}} destroy; \
    fi