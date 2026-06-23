# InternRAG

### TODO

- [ ] Check persistence of Qdrant
- [ ] Solve Docling PDF error
- [ ] Check persistence of Keycloak
- [ ] Improve UI of upload -> is the service okay like this?
- [ ] Test with real data
- [ ] Solve answer token-by-token
- [ ] Add ingress to upload UI
- [ ] Make pipeline async -> study

## Installation
**Linux:** all you have to do is to create a venv and install the needed dependencies:
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install vllm ipykernel vllm-haystack qdrant-haystack docling-haystack
```
**MacOS:** this time it is a little bit more complex:
```bash
curl -fsSL https://raw.githubusercontent.com/vllm-project/vllm-metal/main/install.sh | bash
source ~/.venv-vllm-metal/bin/activate
pip install ipykernel vllm-haystack qdrant-haystack docling-haystack
```
You should then be able to select the kernel from the env.

For MacOS, you should lean on the official GitHub repository: https://github.com/vllm-project/vllm-metal (check the supported models on https://docs.vllm.ai/projects/vllm-metal/en/latest/supported_models/).

> Note: I am probably forgetting a lot of packages

# RAG Pipeline

### Indexing

### Retrieval

# Docker

By running the following commands, images are built and directly pushed to DockerHub (`--push`) so that it is possible for the deployment to use that image when deployed. `--platform linux/amd64` was added so that the image could run on the cluster.

### Indexing

```bash
docker buildx build --platform linux/amd64 -t your-name/your-project:latest -f Dockerfile.indexing --push .
```

### Retrieval

```bash
docker buildx build --platform linux/amd64 -t your-name/your-project:latest -f Dockerfile.retrieval --push .
```

### Upload UI

```bash
docker buildx build --platform linux/amd64 -t your-name/your-project:latest -f Dockerfile.upload --push .
```
