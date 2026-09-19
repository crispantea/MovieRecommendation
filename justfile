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

# Full stack startup
up: auth-service
    {{compose}} up -d --wait

# Tear down all running containers
clean:
    {{compose}} down

# Full wipe (containers down + remove generated secrets)
destroy: clean
    rm -f {{secrets_file}} {{services_dir}}/authorization/import/realm-export.json