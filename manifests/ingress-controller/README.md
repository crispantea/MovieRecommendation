# `Nginx` Ingress Controller

This is a Kubernetes helm chart wrapper for nginx ingress controller.

## Deploy

1. Download the dependencies:
    ```sh
    helm dependency build ./base
    ```

2. Deploy the service:
    ```sh
    helm upgrade --install nginx-ingress ./base \
        --namespace nginx-ingress \
        --create-namespace \
        --wait
    ```

## Remove the Deployment

Delete all resources:
```sh
helm uninstall nginx-ingress -n nginx-ingress
kubectl delete ns nginx-ingress
```