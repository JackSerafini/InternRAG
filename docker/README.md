# Docker

The only active image is the retrieval service, `docker/Dockerfile.retrieval`.
It installs `hayhooks`, `vllm-haystack` and `qdrant-haystack` on `python:3.12-slim`, copies `render/app.py` and the `RAG-Qwen` and `RAG-LAME` wrappers into `/srv`, and starts `uvicorn app:hayhooks` on port `1416`. Hayhooks auto-deploys every wrapper under `HAYHOOKS_PIPELINES_DIR=/srv/pipeline_wrappers`.

Build and push from the **repository root**:

```bash
docker buildx build --platform linux/amd64 -t <dockerhub-user>/rag-retrieval:<tag> -f docker/Dockerfile.retrieval --push .
```

`--push` uploads the image to Docker Hub so the cluster can pull it, and `--platform linux/amd64` makes it run on the cluster nodes. The Deployment in `k8s/retrieval/values.yaml` currently uses `jackserafini/rag-retrieval:test` with `imagePullPolicy: Always`, so after pushing the same tag you only need to restart the pod:

```bash
kubectl rollout restart deployment/rag-retrieval -n orfeo-rag
```

The indexing and upload images of the first prototype are in `archive/initial_rag/` (`Dockerfile.indexing`, `Dockerfile.upload`).
