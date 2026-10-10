# Use the official Ubuntu base image.
FROM ubuntu:latest

# Prevent interactive prompts during package installation.
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists.
RUN apt-get update

# Install facilities.
RUN apt-get install -y supervisor openssh-server iputils-ping unzip jq rsync

# Install additional facilities.
RUN apt-get -y install libssl-dev libffi-dev gnupg python3-dev python3-pip snapd

# Install docker-cli
RUN apt-get update && apt-get install -y curl ca-certificates && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo ${UBUNTU_CODENAME:-$VERSION_CODENAME}) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Install ansible.
RUN apt-get update && apt install -y software-properties-common && \
    apt-add-repository -y -u ppa:ansible/ansible && \
    apt-get update && \
    apt-get install -y ansible

# Install terraform.
RUN wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list
RUN apt-get update && \
    apt-get install -y terraform

# Add graph builder tool for Terraform.
RUN apt-get -y install graphviz

# Install Google Cloud SDK.
#RUN apt-get -y install apt-transport-https
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN wget -O- https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor | tee /usr/share/keyrings/cloud.google.gpg > /dev/null
RUN apt-get update && \
    apt-get -y install google-cloud-cli

# Install Kubernetes Controller.
RUN apt-get -y install kubectl google-cloud-cli-gke-gcloud-auth-plugin

# Create directories for supervisor and sshd
RUN mkdir -p /var/run/sshd /var/log/supervisor

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Clean cache packages
RUN apt-get clean all && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /root

# Executes multiple commands when the container starts:
# - Generates keys to access the machines (created by Terraform) via SSH
# - Supervisor is out "init". Launches ssh and waits forever.
CMD ["sh", "-c", "ssh-keygen -t rsa -b 2048 -N '' -f /root/.ssh/id_rsa && exec /usr/bin/supervisord"]