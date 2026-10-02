# AGI Project

This repository is divided into layers that represent different stages of development and deployment:

- `/infra`: Infrastructure configuration and deployment files
- `/ansible`: Node preparation and server provisioning scripts
- `/services`: Source code and container configuration for application microservices

---

## Deploy

Follow the steps below to fully deploy this project:

1. Deploy the infrastructure:
```sh
docker compose -f services/docker-compose.yml up -d
```

---

## Destroy

Follow the steps below to destroy the project:

1. Destroy the infrastructure:
```sh
docker compose -f services/docker-compose.yml down
```


2. If you want to delete the images:
```sh
docker image rm agi-frontend agi-backend
```
