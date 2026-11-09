# Kubernetes Deployment

This directory contains the Kubernetes configuration used to deploy the InternRAG system and its supporting services.  
The deployment is split into two categories:

* **Helm-based services**, using existing Helm charts:
  * Open WebUI
  * Qdrant

* **Custom InternRAG service**, using a Docker image built for this project:
  * Retrieval (Hayhooks: `RAG-Qwen`, `RAG-LAME` + thumbnail endpoints)

> Keycloak (`k8s/keycloak/`) was used at the beginning for Open WebUI SSO but is **not currently in use**. The manifests are kept for reference only. The generic indexing/upload services of the first prototype have moved to `archive/initial_rag/k8s/`.

The Kubernetes namespace used by the deployment is `orfeo-rag`.

> [!NOTE]
> The `orfeo-rag` namespace is provided by the deployment environment and is not created by this repository.

# Directory Structure

```text
k8s/
├── README.md
├── config.yaml
├── hello_world/        # minimal Deployment/Service/PVC used to test the namespace
├── keycloak/           # not in use
├── net_debug/
│   └── values.yaml
├── open_webui/
│   ├── ingress.yaml
│   └── values.yaml
├── qdrant/
│   ├── ingress.yaml
│   └── values.yaml
└── retrieval/
    ├── service.yaml
    └── values.yaml
```

The `values.yaml` files have two different roles in this repository:

* For **Helm-based services**, they contain values used to customize the corresponding Helm chart
* For the **custom InternRAG services**, despite their name, they are actually Kubernetes `Deployment` manifests and are applied directly with `kubectl`

## Prerequisites

The deployment requires:

* Access to the Kubernetes cluster
* `kubectl`
* Helm
* Access to the Docker images used by the custom services
* The required API credentials and secrets

The required Helm repositories are:

* qdrant: https://qdrant.github.io/qdrant-helm
* open-webui: https://helm.openwebui.com/
<!-- * codecentric: https://codecentric.github.io/helm-charts -->

They can be added with:

```bash
helm repo add qdrant https://qdrant.github.io/qdrant-helm
helm repo add open-webui https://helm.openwebui.com/

helm repo update
```
<!-- helm repo add codecentric https://codecentric.github.io/helm-charts -->

# Shared Configuration

The file `k8s/config.yaml` contains a Kubernetes `ConfigMap` with configuration shared by the InternRAG services.  
The current configuration is:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-config
  namespace: orfeo-rag
data:
  VLLM_API_URL: "https://orfeo-llm.areasciencepark.it/vllm/v1"
  QDRANT_URL: "http://qdrant.orfeo-rag.svc.cluster.local:6333"
```

The variables are:

| Variable       | Description                                       |
| -------------- | ------------------------------------------------- |
| `VLLM_API_URL` | URL of the vLLM OpenAI-compatible API             |
| `QDRANT_URL`   | Internal Kubernetes address of the Qdrant service |

The ConfigMap can be applied with:

```bash
kubectl apply -f k8s/config.yaml
```

The Qdrant address uses Kubernetes DNS rather than `localhost` because the application services and Qdrant run in different pods.

## Resource Limits

Resource requests and limits must be specified for the containers deployed in this environment. For example:

```yaml
resources:
  requests:
    cpu: 1
    memory: 1Gi
  limits:
    cpu: 2
    memory: 8Gi
```

When adding or modifying a deployment, make sure that appropriate resource requests and limits are defined.

# Helm Deployments

Qdrant and Open WebUI are deployed using existing Helm charts.  
Their deployment-specific configuration is stored in the corresponding directories.

## Qdrant

Qdrant is used as the vector database for the RAG system.

The Helm configuration is located at `k8s/qdrant/values.yaml`.  
Install or upgrade Qdrant with:

```bash
helm upgrade --install qdrant qdrant/qdrant -f k8s/qdrant/values.yaml
```

To uninstall it:

```bash
helm uninstall qdrant
kubectl delete pvc -l app.kubernetes.io/instance=qdrant
# kubectl delete pvc qdrant-storage-qdrant-0 -n orfeo-rag # to delete a specific one
```

The Qdrant service is accessed internally by the InternRAG services through `qdrant.orfeo-rag.svc.cluster.local:6333`. This address is configured through `rag-config`.

<!-- ## Keycloak

Keycloak provides authentication and identity management for the deployment.

The project uses the community-maintained KeycloakX Helm chart.  
Install or upgrade Keycloak with:

```bash
helm upgrade --install keycloak codecentric/keycloakx -f k8s/keycloak/values.yaml
```

To uninstall it:

```bash
helm uninstall keycloak
```

### Ingress

Keycloak is exposed through `k8s/keycloak/ingress.yaml`.  
Apply the ingress with:

```bash
kubectl apply -f k8s/keycloak/ingress.yaml
```

The configured local hostname is:

```text
auth.local
```

For local access, add the ingress IP to `/etc/hosts`:

```text
10.128.18.132    auth.local
``` -->

## Open WebUI

Open WebUI provides the user-facing interface for interacting with the deployed models and the InternRAG retrieval service.

The Helm configuration is located at `k8s/open_webui/values.yaml`.  
Install or upgrade Open WebUI with:

```bash
helm upgrade --install open-webui open-webui/open-webui -f k8s/open_webui/values.yaml
```

To uninstall it:

```bash
helm uninstall open-webui
kubectl delete pvc -l app.kubernetes.io/instance=open-webui
```

Open WebUI is configured with two OpenAI-compatible connections (`openaiBaseApiUrls` in `values.yaml`):

1. `https://orfeo-llm.areasciencepark.it/vllm/v1`: the Orfeo vLLM gateway (plain models)
2. `http://rag-retrieval.orfeo-rag.svc.cluster.local:1416/v1`: the InternRAG retrieval service (models `RAG-Qwen`, `RAG-LAME`)

### Ingress

`k8s/open_webui/ingress.yaml` exposes Open WebUI at `llm-rag.dev.rd.areasciencepark.it`. On the same host it routes:

| Path | Backend |
| ---- | ------- |
| `/` | `open-webui:80` |
| `/rag-images` | `rag-retrieval:1416` (SEM thumbnails) |
| `/rag-images-lame` | `rag-retrieval:1416` (LAME thumbnails) |

```bash
kubectl apply -f k8s/open_webui/ingress.yaml
```

The thumbnail routes must stay on the same host, because the image links in the RAG answers point to it.

<!-- ## Open WebUI Authentication

Open WebUI is configured to use Keycloak for authentication through OpenID Connect (OIDC).  
The setup follows the [Open WebUI Keycloak SSO documentation](https://docs.openwebui.com/features/authentication-access/auth/sso/keycloak/).

### Keycloak Client

First, create a realm in Keycloak (e.g., orfeo). Then create an OpenID Connect client:

1. Set *Client ID*: open-webui
2. Enable client authentication
3. Set *Valid redirect URIs*: http://chat.local/oauth/oidc/callback
4. Set *Web origins*: http://chat.local
5. Save and create the Client
6. Open its **Credentials** tab and retrieve the generated Client Secret
7. Create a test user (e.g., admin) and set a new password (e.g., admin) in the Credentials tab (remember to uncheck temporary)

### Open WebUI OIDC Secret

The Keycloak client secret is stored as a Kubernetes secret.  
Check whether the secret already exists:

```bash
kubectl get secrets
```

If necessary, delete the existing secret:

```bash
kubectl delete secret open-webui-oidc
```

Create the secret using the *Client Secret* found in the Credentials tab of the Client created in Keycloak:

```bash
kubectl create secret generic open-webui-oidc --from-literal=client-secret='XXX'
```

> NOTE: this is currently a simple development setup. A dedicated secret-management solution should be considered for a production deployment. -->

# vLLM Credentials

The models used by Open WebUI are hosted on Orfeo and require an API key.  
The key is stored in Kubernetes as a secret. The current configuration uses:

```bash
kubectl create secret generic vllm-api-keys --from-literal=api-keys='XXX;dummy'
```

The two values correspond to the two configured API endpoints.  
The first endpoint requires authentication to access the models. The second endpoint currently has its authentication handled elsewhere, but Open WebUI still requires a second value, hence the `dummy` value.

The **RAG pipelines** use a separate Kubernetes secret for accessing the vLLM API. This secret is named `vllm-api-key`, and the pipelines retrieve the API key directly from it:

```bash
kubectl create secret generic vllm-api-key --from-literal=api-key='XXX'
```
Therefore, both secrets may be required for a complete deployment:

* `vllm-api-keys` → used by **Open WebUI**
* `vllm-api-key` → used by the **InternRAG RAG pipelines**

The actual API key should never be committed to the repository.

# Custom InternRAG Services

The indexing, retrieval, and upload components are developed specifically for InternRAG.  
Unlike Open WebUI and Qdrant, they are not deployed through third-party Helm charts. Instead, each service is packaged into a Docker image and deployed using Kubernetes manifests.

The three services are:

```text
Retrieval
   ├── Docker image
   └── Kubernetes Deployment + Service

Indexing
   ├── Docker image
   └── Kubernetes Deployment + Service

Upload
   ├── Docker image
   └── Kubernetes Deployment + Service
```

## Retrieval

The retrieval service exposes the InternRAG retrieval pipelines as OpenAI-compatible APIs through [Hayhooks](https://github.com/deepset-ai/hayhooks) so that Open WebUI can interact with them as models.  
The service currently contains two Haystack pipeline wrappers:

* `RAG-Qwen`: SEM dataset, collection `SEM_qwen`
* `RAG-LAME`: LAME dataset, collection `LAME_qwen`

(`RAG-Test` exists in `pipeline_wrappers/` but is not included in the image.)

The Docker image is defined by `docker/Dockerfile.retrieval`: it includes the `RAG-Qwen` and `RAG-LAME` wrappers and `render/app.py` (Hayhooks app + `/rag-images` and `/rag-images-lame thumbnail` endpoints), which creates the Hayhooks application and provides an additional endpoint for retrieving SEM image thumbnails from Qdrant.

The container runs Hayhooks through Uvicorn on port `1416`. Hayhooks automatically discovers the pipeline wrappers under the configured pipelines directory.

The Kubernetes configuration is located at:

```text
k8s/retrieval/
├── values.yaml
└── service.yaml
```

As with the other custom InternRAG services, `values.yaml` is a Kubernetes `Deployment` manifest rather than a Helm values file.  
The service uses the shared `rag-config` ConfigMap for the vLLM and Qdrant URLs and obtains the vLLM API key from the Kubernetes secret: `vllm-api-key`.  
Deploy the service with:

```bash
kubectl apply -f k8s/retrieval/values.yaml
kubectl apply -f k8s/retrieval/service.yaml
```

To remove it:

```bash
kubectl delete -f k8s/retrieval/
```

The retrieval service is then available to other services in the Kubernetes cluster through its Kubernetes Service.

For details about the retrieval pipelines themselves, see [`docs/retrieval.md`](../docs/retrieval.md).

## Archived services

The generic indexing and upload services of the first prototype are in `archive/initial_rag/k8s/{indexing,upload}/`. They are not deployed.

# Development Utilities

## Net Debug

The `net_debug` deployment is a utility used to investigate networking and connectivity inside the Kubernetes cluster.  

```bash
kubectl apply -f k8s/net_debug/values.yaml
kubectl delete -f k8s/net_debug/values.yaml
```

## Hello World

`k8s/hello_world/` contains a minimal Deployment, Service and PVC used to test access to the namespace and storage:

```bash
kubectl apply -f k8s/hello_world/
kubectl delete -f k8s/hello_world/
```

# Checking the Deployment

The following commands are useful for checking the state of the cluster:

```bash
kubectl get pods -n orfeo-rag
kubectl get services -n orfeo-rag
kubectl get deployments -n orfeo-rag
kubectl get secrets -n orfeo-rag
kubectl get configmaps -n orfeo-rag
```

To inspect a pod:

```bash
kubectl describe pod <pod-name> -n orfeo-rag
```

To inspect its logs:

```bash
kubectl logs <pod-name> -n orfeo-rag
```
