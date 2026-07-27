import base64
import os

from fastapi import HTTPException
from fastapi.responses import Response
from hayhooks import create_app
from qdrant_client import QdrantClient, models

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant.orfeo-rag.svc.cluster.local:6333")
QDRANT_COLLECTION = "SEMImages_qwen"

# This is what hayhooks run / your uvicorn entrypoint serves --
# it still auto-deploys pipelines from HAYHOOKS_PIPELINES_DIR at startup.
hayhooks = create_app()

_qdrant_client = QdrantClient(url=QDRANT_URL)


@hayhooks.get("/rag-images/{image_id}.png")
async def get_thumbnail(image_id: int):
    points, _ = _qdrant_client.scroll(
        collection_name=QDRANT_COLLECTION,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="meta.SEMImageID",
                    match=models.MatchValue(value=image_id),
                )
            ]
        ),
        with_payload=["meta.thumb_b64"],
        limit=1,
    )
    if not points or not points[0].payload.get("meta", {}).get("thumb_b64"):
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    data_uri = points[0].payload["meta"]["thumb_b64"]
    _, b64_data = data_uri.split(",", 1)  # strip "data:image/png;base64," prefix
    image_bytes = base64.b64decode(b64_data)
    return Response(content=image_bytes, media_type="image/png")