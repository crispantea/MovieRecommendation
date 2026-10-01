set dotenv-load := true
set shell       := ["bash", "-euo", "pipefail", "-c"]

# --------------------------------------------------------------
# VARIABLES
# --------------------------------------------------------------

# Env Files
secrets_file := ".env.secrets"
env_file     := ".env"

# Directories
services_dir := "services"
scripts_dir  := "scripts"
tf_dir       := "infra/environments/dev"
ansible_dir  := "ansible"
manifests_dir := "manifests"

# This uses the variables defined in the env files provided and fills the required vars in the docker compose file
compose      := "docker compose --env-file " + env_file + " --env-file " + secrets_file + " -f " + services_dir + "/docker-compose.yml"

# --------------------------------------------------------------
# EXPORTED VARIABLES - needed across scripts
# --------------------------------------------------------------

export SERVICES_DIR := services_dir
export SECRETS_FILE := secrets_file

# ------------------------------------------------------------------------------------------------ #
# Local / Docker Compose Stack
# ------------------------------------------------------------------------------------------------ #
tf_auth_dir := tf_dir + "/auth"

# Initialize secrets and hydrate keycloak templates
local-init:
    bash {{scripts_dir}}/bootstrap.sh

# Start Keycloak container and wait until ready/healthy
local-auth-service:
    {{compose}} up -d --wait auth-service
    . {{scripts_dir}}/terraform/keycloak/load-env.sh && \
    terraform -chdir={{tf_auth_dir}} init -input=false && \
    terraform -chdir={{tf_auth_dir}} apply -auto-approve

local-build:
    {{compose}} build --no-cache

# Full stack startup
local-up: local-auth-service
    {{compose}} up -d --wait

# Tear down all running containers
local-down:
    {{compose}} down

# Full wipe (containers down + remove generated secrets)
local-destroy: local-down
    rm -f {{secrets_file}} {{services_dir}}/authorization/import/realm-export.json

# ------------------------------------------------------------------------------------------------ #
# Local Kubernetes / Kind Stack
# ------------------------------------------------------------------------------------------------ #
cluster_name := "cluster-psia2026"

kind-init:
    kind create cluster --config="{{manifests_dir}}/kind-cluster.yaml" --name={{cluster_name}}

kind-load-images: kind-init
    kind load docker-image agi-frontend:latest --name cluster-psia2026

kind-deploy: kind-load-images
    # Ingress Controller
    helm dependency build "{{manifests_dir}}/ingress-controller/base"
    helm upgrade --install nginx-ingress "{{manifests_dir}}/ingress-controller/base" --namespace nginx-ingress --create-namespace --wait

    # Frontend
    kubectl apply -k "{{manifests_dir}}/frontend/overlays/prod"

kind-destroy:
    kind delete cluster --name={{cluster_name}}

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