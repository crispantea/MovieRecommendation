set dotenv-load := true
# set dotenv-filename = [".env", ".env.secrets"] # TODO: This only works on newer justfile versions ...
set export := true

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

export SERVICES_DIR  := services_dir
export SECRETS_FILE  := secrets_file
export MANIFESTD_DIR := manifests_dir

# ------------------------------------------------------------------------------------------------ #
# Global
# ------------------------------------------------------------------------------------------------ #

# Initialize secrets and hydrate keycloak templates
init:
    bash {{scripts_dir}}/bootstrap.sh

destroy:
    rm -f {{secrets_file}} \
          {{services_dir}}/authorization/import/realm-export.json \
          {{manifests_dir}}/keycloak/base/realm-export.json

# ------------------------------------------------------------------------------------------------ #
# Local / Docker Compose Stack
# ------------------------------------------------------------------------------------------------ #
tf_auth_dir := tf_dir + "/auth"

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
    kind create cluster --config="{{manifests_dir}}/kind-cluster.yaml" --name={{cluster_name}}

kind-load-images: kind-init
    kind load docker-image agi-frontend:latest --name cluster-psia2026
    kind load docker-image agi-profiles-service:latest --name cluster-psia2026

kind-deploy: kind-load-images
    # Apply the Gateway API CRDs
    kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.1/standard-install.yaml

    # Apply kgateway specific CRDs that will be used to define the type of proxy that will be created
    helm upgrade -i kgateway-crds oci://cr.kgateway.dev/kgateway-dev/charts/kgateway-crds \
    --create-namespace -n kgateway-system --version 2.4.5

    # Build and deploy the kgateway wrapper (already comes with the gateway definition)
    helm dependency build "{{manifests_dir}}/kgateway/base"
    helm upgrade -i kgateway "{{manifests_dir}}/kgateway/base" -n kgateway-system --create-namespace --wait

    # Deploy Frontend
    kubectl apply -k "{{manifests_dir}}/frontend/overlays/prod"  --wait

    # Build and deploy keyclaok wrapper (already comes with the httproute, secrets and configmap used on keycloak)
    helm dependency build "{{manifests_dir}}/keycloak/base"

    # Ugly workaround because apt justfile version is very old and therefore this:
    # set dotenv-filename = [".env", ".env.secrets"]  doesnt work in the current version, we can update it, but it
    # requires everyone to update it using binary installation
    set -a; [ -f {{env_file}} ] && . ./{{env_file}}; [ -f {{secrets_file}} ] && . ./{{secrets_file}}; set +a; \
    envsubst < "{{manifests_dir}}/keycloak/base/values.yaml" | \
    helm upgrade --install keycloak "{{manifests_dir}}/keycloak/base" \
    -n keycloak \
    --create-namespace \
    --wait \
    -f -

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