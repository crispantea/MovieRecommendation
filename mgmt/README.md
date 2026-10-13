# Management Environment

This directory contains the files needed to build a Docker image with tools for infrastructure automation and cloud management.

## Files

* `Dockerfile` — builds the Docker image.
* `supervisord.conf` — configures Supervisor and SSH.

## Included Tools

The image is based on Ubuntu and includes:

* Terraform
* Ansible
* Google Cloud CLI
* kubectl
* Docker CLI
* SSH
* Python 3
* Graphviz

## Run

From the repository root, after initializing configuration:

```bash
ENV=cloud just mgmt-up
docker exec -it -w /root/agi-project mgmt bash
```

`mgmt-up` builds and starts the container with the project directory and Docker socket mounted. Stop it with:

```bash
ENV=cloud just mgmt-down
```
