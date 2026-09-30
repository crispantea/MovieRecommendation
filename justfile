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

# TDB ...

# ------------------------------------------------------------------------------------------------ #
# Cloud Kubernetes / Production Stack
# ------------------------------------------------------------------------------------------------ #
project_dir := "/root/agi-project"
tf_gcp_dir := tf_dir + "/gcp"

target := ""
cmd := if target != "" { "docker exec -it " + target + " " } else { "" }

mgmt-up:
	docker build -t mgmt ./mgmt
	docker run --rm --name mgmt --hostname mgmt -v "$(pwd):{{project_dir}}" -d mgmt

mgmt-down:
	docker stop mgmt

cloud-init target="":
    {{cmd}} terraform -chdir={{tf_gcp_dir}} init

cloud-plan target="":
    {{cmd}} terraform -chdir={{tf_gcp_dir}} plan

# TODO: Add a sort of a health check to the ansible files because it fails if 
cloud-apply target="":
    {{cmd}} terraform -chdir={{tf_gcp_dir}} apply
    {{cmd}} ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i "{{ansible_dir}}/gcphosts" "{{ansible_dir}}/ansible-gcp-configure-nodes.yml"
    {{cmd}} ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i "{{ansible_dir}}/gcphosts" "{{ansible_dir}}/ansible-k8s-install.yml"
    {{cmd}} ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i "{{ansible_dir}}/gcphosts" "{{ansible_dir}}/ansible-create-cluster.yml"
    {{cmd}} ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i "{{ansible_dir}}/gcphosts" "{{ansible_dir}}/ansible-workers-join.yml"

cloud-output target="":
    {{cmd}} terraform -chdir={{tf_gcp_dir}} output

cloud-destroy target="":
    {{cmd}} terraform -chdir={{tf_gcp_dir}} destroy