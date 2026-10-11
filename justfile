set dotenv-load
set shell := ["bash", "-euo", "pipefail", "-c", ': "${ENV?ENV is required, e.g. ENV=local just up}"; set -a; . ".env.$ENV"; if [ -f .env.disks ]; then . .env.disks; fi; if [[ "$ENV" == "cloud" || "$ENV" == "kind" ]]; then . .env.kube; fi; eval "$0"']

# --------------------------------------------------------------
# Variables
# --------------------------------------------------------------

# Env Files
global_env_file  := ".env"
local_env_file   := ".env.local"
kind_env_file    := ".env.kind"
cloud_env_file   := ".env.cloud"
secrets_env_file := ".env.secrets"
disks_env_file   := ".env.disks"

# Directories
services_dir := "services"
scripts_dir  := "scripts"
tf_dir       := "infra"
ansible_dir  := "ansible"
manifests_dir := "manifests"

tf_dev_dir := tf_dir + "/environments/dev"
tf_dev_auth_dir := tf_dev_dir + "/auth"
tf_dev_grafana_dir := tf_dev_dir + "/grafana"

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
    docker image pull ${INFERENCE_OLLAMA_IMAGE_REPO}:${INFERENCE_OLLAMA_IMAGE_TAG}

destroy:
    rm -f {{secrets_env_file}} \
          {{disks_env_file}} \
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
local-init-keycloak: init
    {{compose}} up -d --wait auth-service
    set -a; source {{secrets_env_file}}; set +a && \
    . {{scripts_dir}}/terraform/keycloak/export-input-vars.sh && \
    terraform -chdir={{tf_dev_auth_dir}} init -input=false && \
    terraform -chdir={{tf_dev_auth_dir}} apply -auto-approve

# Full stack startup
local-up: local-init-keycloak
    {{compose}} up -d --wait

# Manually trigger movie dataset loading from movies.csv.gz
seed-movies:
    docker exec -it movies-service python seed_db.py

# Reload movie catalog from scratch (clears existing entries)
seed-movies-reload:
    docker exec -it movies-service python seed_db.py --drop-existing

# Tear down all running containers
local-clean:
    {{compose}} down --volumes --remove-orphans

# Full wipe (containers down + remove generated secrets)
local-destroy: local-clean destroy

# ------------------------------------------------------------------------------------------------ #
# Local Kubernetes / Kind Stack
# ------------------------------------------------------------------------------------------------ #
cluster_name := "cluster-psia2026"

kind-init:
    # Create kind cluster (if doesnt exist)
    kind get clusters | grep -qx "{{cluster_name}}" || kind create cluster --config="{{manifests_dir}}/kind-cluster.yaml" --name={{cluster_name}}
    kind load docker-image ${PROFILES_SERVICE_IMAGE}:latest --name={{cluster_name}}
    kind load docker-image ${MOVIES_SERVICE_IMAGE}:latest --name={{cluster_name}}
    # The line bellow causes errors on some docker versions, we will pull it directly when manifests need it instead
    # of loading it into the cluster
    # kind load docker-image ${INFERENCE_OLLAMA_IMAGE_REPO}:${INFERENCE_OLLAMA_IMAGE_TAG} --name={{cluster_name}}
    kind load docker-image ${FRONTEND_IMAGE}:latest --name={{cluster_name}}
    kind load docker-image ${INFERENCE_SERVICE_IMAGE}:latest --name={{cluster_name}}

kube-prepare:
    # ---- Add required Helm repos  ----
    helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts

    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo add otwld https://helm.otwld.com/
    helm repo update

    # Apply the Gateway API CRDs
    kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.1/standard-install.yaml

    # Apply kgateway specific CRDs that will be used to define the type of proxy that will be created
    helm upgrade -i kgateway-crds oci://cr.kgateway.dev/kgateway-dev/charts/kgateway-crds \
    -n ${KGATEWAY_NAMESPACE} \
    --create-namespace \
    --version 2.4.5 \
    --wait


kube-deploy-kgateway:
    # Build and deploy the kgateway wrapper (already comes with the gateway definition)
    helm dependency build "{{manifests_dir}}/kgateway/base"
    helm upgrade -i kgateway "{{manifests_dir}}/kgateway/base" \
    -n ${KGATEWAY_NAMESPACE} \
    --create-namespace \
    --wait

kube-deploy-keycloak:
    # Build and deploy the keyclaok wrapper (already comes with the httproute, secrets and configmap used on keycloak)
    helm dependency build "{{manifests_dir}}/keycloak/base"
    set -a; source {{secrets_env_file}}; set +a && \
    envsubst < "{{manifests_dir}}/keycloak/base/values.yaml" | \
    helm upgrade --install keycloak "{{manifests_dir}}/keycloak/base" \
    -n ${KEYCLOAK_NAMESPACE} \
    --create-namespace \
    --wait \
    -f -

    # Initialize keycloak resources using terraform
    set -a; source {{secrets_env_file}}; set +a && \
    . {{scripts_dir}}/terraform/keycloak/export-input-vars.sh && \
    terraform -chdir={{tf_dev_auth_dir}} init -input=false && \
    terraform -chdir={{tf_dev_auth_dir}} apply -auto-approve

kube-deploy-profiles-service:
    # Build and deploy the profiles-service wrapper
    helm dependency build "{{manifests_dir}}/profiles-service/database"
    set -a; source {{secrets_env_file}}; set +a && \
    envsubst < "{{manifests_dir}}/profiles-service/database/values.yaml" | \
    helm upgrade --install postgresql "{{manifests_dir}}/profiles-service/database" \
    -n ${PROFILES_NAMESPACE} \
    --create-namespace \
    --wait \
    -f -

    set -a; source {{secrets_env_file}}; set +a && \
    if [ "${KEYCLOAK_HOST_PORT}" = "80" ] || [ "${KEYCLOAK_HOST_PORT}" = "443" ] || [ -z "${KEYCLOAK_HOST_PORT}" ]; then \
        PORT_SUFFIX="" ; \
    else \
        PORT_SUFFIX=":${KEYCLOAK_HOST_PORT}" ; \
    fi && \
    export KEYCLOAK_ISSUER="http://${APP_DOMAIN}${PORT_SUFFIX}${KEYCLOAK_PATH}/realms/${KEYCLOAK_APP_REALM}" && \
    kubectl kustomize "{{manifests_dir}}/profiles-service/overlays/$ENV" | envsubst | kubectl apply -f - --wait

kube-deploy-movies-service:
    # Build and deploy the movies-service database wrapper
    helm dependency build "{{manifests_dir}}/movies-service/database"
    set -a; source {{secrets_env_file}}; set +a && \
    envsubst < "{{manifests_dir}}/movies-service/database/values.yaml" | \
    helm upgrade --install postgresql "{{manifests_dir}}/movies-service/database" \
    -n ${MOVIES_NAMESPACE} \
    --create-namespace \
    --wait \
    -f -

    set -a; source {{secrets_env_file}}; set +a && \
    kubectl kustomize "{{manifests_dir}}/movies-service/overlays/prod" | envsubst | kubectl apply -f - --wait

kube-deploy-inference-service:
    # Build and deploy the ollama wrapper
    helm dependency build "{{manifests_dir}}/inference-service/ollama"
    envsubst < "{{manifests_dir}}/inference-service/ollama/values.yaml" | \
    helm upgrade --install ollama "{{manifests_dir}}/inference-service/ollama" \
    -n ${INFERENCE_NAMESPACE} \
    --create-namespace \
    --wait --timeout 20m \
    -f -

    if [ "${KEYCLOAK_HOST_PORT}" = "80" ] || [ "${KEYCLOAK_HOST_PORT}" = "443" ] || [ -z "${KEYCLOAK_HOST_PORT}" ]; then \
        PORT_SUFFIX="" ; \
    else \
        PORT_SUFFIX=":${KEYCLOAK_HOST_PORT}" ; \
    fi && \
    export KEYCLOAK_ISSUER="http://${APP_DOMAIN}${PORT_SUFFIX}${KEYCLOAK_PATH}/realms/${KEYCLOAK_APP_REALM}" && \
    kubectl kustomize "{{manifests_dir}}/inference-service/overlays/$ENV" | envsubst | kubectl apply -f - --wait

kube-deploy-frontend:
    kubectl kustomize "{{manifests_dir}}/frontend/overlays/$ENV" | envsubst | kubectl apply -f - --wait

kube-deploy-mimir:
    helm dependency build "{{manifests_dir}}/observability/mimir"
    helm upgrade --install mimir "{{manifests_dir}}/observability/mimir" \
    -n ${MIMIR_NAMESPACE} \
    --create-namespace \
    -f "{{manifests_dir}}/observability/mimir/values.yaml" \
    --wait

kube-deploy-grafana:
    helm dependency build "{{manifests_dir}}/observability/grafana"
    set -a; source {{secrets_env_file}}; set +a && \
    envsubst < "{{manifests_dir}}/observability/grafana/values.yaml" | \
    helm upgrade --install grafana "{{manifests_dir}}/observability/grafana" \
    -n ${GRAFANA_NAMESPACE} \
    --create-namespace \
    --wait \
    -f -

    # Initialize grafana resources using terraform
    set -a; source {{secrets_env_file}}; set +a && \
    . {{scripts_dir}}/terraform/grafana/export-input-vars.sh && \
    terraform -chdir={{tf_dev_grafana_dir}} init -input=false && \
    terraform -chdir={{tf_dev_grafana_dir}} apply -auto-approve

kube-deploy-otel:
    helm dependency build "{{manifests_dir}}/observability/otel"
    envsubst < "{{manifests_dir}}/observability/otel/values.yaml" | \
    helm upgrade --install ${OTEL_RELEASE_NAME} "{{manifests_dir}}/observability/otel" \
    -n ${OTEL_NAMESPACE} \
    --create-namespace \
    --wait \
    -f -

kube-deploy: kube-prepare kube-deploy-kgateway kube-deploy-keycloak kube-deploy-profiles-service kube-deploy-movies-service kube-deploy-inference-service kube-deploy-frontend kube-deploy-mimir kube-deploy-grafana kube-deploy-otel

kube-clean-kgateway:
    helm uninstall kgateway -n ${KGATEWAY_NAMESPACE}
    kubectl delete ns ${KGATEWAY_NAMESPACE} --wait

kube-clean-keycloak:
    helm uninstall keycloak -n ${KEYCLOAK_NAMESPACE}
    kubectl delete ns ${KEYCLOAK_NAMESPACE} --wait

kube-clean-profiles-service:
    helm uninstall postgresql -n ${PROFILES_NAMESPACE}
    kubectl kustomize "{{manifests_dir}}/profiles-service/overlays/$ENV" | envsubst | kubectl delete -f - --wait

kube-clean-movies-service:
    helm uninstall postgresql -n ${MOVIES_NAMESPACE}
    kubectl kustomize "{{manifests_dir}}/movies-service/overlays/prod" | envsubst | kubectl delete -f - --wait

kube-clean-inference-service:
    helm delete ollama -n ${INFERENCE_NAMESPACE} --wait

kube-clean-frontend:
    kubectl kustomize "{{manifests_dir}}/frontend/overlays/$ENV" | envsubst | kubectl delete -f - --wait

kube-clean-mimir:
    helm uninstall mimir -n ${MIMIR_NAMESPACE}
    kubectl delete ns ${MIMIR_NAMESPACE} --wait

kube-clean-grafana:
    helm uninstall grafana -n ${GRAFANA_NAMESPACE}
    kubectl delete ns ${GRAFANA_NAMESPACE} --wait

kube-clean-otel:
    helm uninstall opentelemetry-collector -n ${OTEL_NAMESPACE}
    kubectl delete ns ${OTEL_NAMESPACE} --wait

kube-clean: kube-clean-monitoring kube-clean-grafana kube-clean-mimir kube-clean-frontend kube-clean-inference-service kube-clean-movies-service kube-clean-profiles-service kube-clean-keycloak kube-clean-kgateway

kind-up: kind-init kube-deploy

kind-clean:
    kind delete cluster --name={{cluster_name}}

kind-destroy: kind-clean destroy

# ------------------------------------------------------------------------------------------------ #
# Cloud Kubernetes / Production Stack
# ------------------------------------------------------------------------------------------------ #
tf_gcp_dir := tf_dev_dir + "/gcp"

mgmt_cmd := "docker exec -it mgmt"
mgmt_project_dir := "/root/agi-project"
mgmt_tf_gcp_dir := mgmt_project_dir + "/" + tf_gcp_dir
mgmt_ansible_dir := mgmt_project_dir + "/" + ansible_dir

mgmt-up:
	docker build -t mgmt ./mgmt
	docker run -v /var/run/docker.sock:/var/run/docker.sock --rm --name mgmt --hostname mgmt -v "$(pwd):{{mgmt_project_dir}}" -d mgmt

mgmt-down:
	docker stop mgmt

cloud-infra-init target="":
    if [ "{{target}}" = "local" ]; then \
        terraform -chdir={{tf_gcp_dir}} init; \
    else \
        {{mgmt_cmd}} terraform -chdir={{mgmt_tf_gcp_dir}} init; \
    fi

cloud-infra-plan target="":
    if [ "{{target}}" = "local" ]; then \
        terraform -chdir={{tf_gcp_dir}} plan; \
    else \
        {{mgmt_cmd}} terraform -chdir={{mgmt_tf_gcp_dir}} plan; \
    fi

cloud-infra-apply target="":
    if [ "{{target}}" = "local" ]; then \
        terraform -chdir={{tf_gcp_dir}} apply && \
        terraform -chdir={{tf_gcp_dir}} output -json disks | \
        jq -r 'to_entries[] | "\(.key | ascii_upcase)_VOLUME_HANDLE=\(.value.volume_handle)"' \
        > {{disks_env_file}}; \
    else \
        {{mgmt_cmd}} terraform -chdir={{mgmt_tf_gcp_dir}} apply && \
        {{mgmt_cmd}} sh -c 'terraform -chdir={{mgmt_tf_gcp_dir}} output -json disks | jq -r '\''to_entries[] | "\(.key | ascii_upcase)_VOLUME_HANDLE=\(.value.volume_handle)"'\'' > {{mgmt_project_dir}}/{{disks_env_file}}'; \
    fi

cloud-ansible target="": (cloud-infra-apply target)
    if [ "{{target}}" = "local" ]; then \
        ANSIBLE_CONFIG="{{ansible_dir}}/ansible.cfg" ansible-playbook "{{ansible_dir}}/site.yml"; \
    else \
        {{mgmt_cmd}} env ANSIBLE_CONFIG="{{mgmt_ansible_dir}}/ansible.cfg" ansible-playbook "{{mgmt_ansible_dir}}/site.yml"; \
    fi

cloud-infra-output target="":
    if [ "{{target}}" = "local" ]; then \
        terraform -chdir={{tf_gcp_dir}} output; \
    else \
        {{mgmt_cmd}} terraform -chdir={{mgmt_tf_gcp_dir}} output; \
    fi

cloud-infra-destroy target="":
    if [ "{{target}}" = "local" ]; then \
        terraform -chdir={{tf_gcp_dir}} destroy -target=module.compute -target=module.network; \
    else \
        {{mgmt_cmd}} terraform -chdir={{mgmt_tf_gcp_dir}} destroy -target=module.compute -target=module.network; \
    fi

cloud-init target="":
    kubectl apply -f "{{manifests_dir}}/storage-class.yaml"
    kubectl create namespace gce-pd-csi-driver --dry-run=client -o yaml | kubectl apply -f -
    kubectl -n gce-pd-csi-driver create secret generic cloud-sa --from-file=cloud-sa.json={{tf_gcp_dir}}/credentials.json --dry-run=client -o yaml | kubectl apply -f -
    kubectl apply -k "github.com/kubernetes-sigs/gcp-compute-persistent-disk-csi-driver/deploy/kubernetes/overlays/stable-master?ref=master"

cloud-up target="": (cloud-infra-apply target) (cloud-ansible target) (cloud-init target) kube-deploy

cloud-clean target="": (cloud-infra-destroy target)

cloud-destroy target="": (cloud-infra-destroy target) destroy
    if [ "{{target}}" = "local" ]; then \
        terraform -chdir={{tf_gcp_dir}} destroy; \
    else \
        {{mgmt_cmd}} terraform -chdir={{mgmt_tf_gcp_dir}} destroy; \
    fi
