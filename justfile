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

# This uses the variables defined in the env files provided and fills the required vars in the docker compose file
compose      := "docker compose --env-file " + env_file + " --env-file " + secrets_file + " -f " + services_dir + "/docker-compose.yml"

# --------------------------------------------------------------
# EXPORTED VARIABLES - needed across scripts
# --------------------------------------------------------------

export SERVICES_DIR := services_dir
export SECRETS_FILE := secrets_file

# --------------------------------------------------------------

# Initialize secrets and hydrate keycloak templates
init:
    bash {{scripts_dir}}/bootstrap.sh

# Start Keycloak container and wait until ready/healthy
auth-service:
    {{compose}} up -d --wait auth-service
    . {{scripts_dir}}/terraform/keycloak/load-env.sh && \
    terraform -chdir={{tf_dir}} init -input=false && \
    terraform -chdir={{tf_dir}} apply -auto-approve -target=module.auth

build:
    {{compose}} build --no-cache

# Full stack startup
up: auth-service
    {{compose}} up -d --wait

# Tear down all running containers
clean:
    {{compose}} down

# Full wipe (containers down + remove generated secrets)
destroy: clean
    rm -f {{secrets_file}} {{services_dir}}/authorization/import/realm-export.json

# ================================================================================================ #
# ========== Infrastructure ====================================================================== #
# ================================================================================================ #
project_dir := "/root/agi-project"
infra_dir := project_dir + "/infra-gc"

mgmt-up:
	docker build -t mgmt ./mgmt
	docker run --rm --name mgmt --hostname mgmt -v "$(pwd):{{project_dir}}" -d mgmt

mgmt-down:
	docker stop mgmt

infra-init:
    docker exec -it mgmt terraform -chdir={{infra_dir}} init

infra-plan:
    docker exec -it mgmt terraform -chdir={{infra_dir}} plan

infra-apply:
    docker exec -it mgmt terraform -chdir={{infra_dir}} apply

infra-destroy:
    docker exec -it mgmt terraform -chdir={{infra_dir}} destroy