# `Profiles` Service

These are the necessary Kubernetes manifests to deploy the profiles service.

## Deploy

1. Deploy the service:
    ```sh
    kubectl apply -k overlays/prod
    ```

## Remove the Deployment

Delete all resources:
```sh
kubectl delete -k overlays/prod
```