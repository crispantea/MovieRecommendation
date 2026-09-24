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
* SSH
* Python 3
* Graphviz

## Build

```bash
docker build -t mgmt .
```

## Run

```bash
docker run -d --name mgmt mgmt
```

To access the container:

```bash
docker exec -it mgmt bash
```
