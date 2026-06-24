"""
Minimal upload UI for the indexing service.
A single page with a file-upload form that POSTs to the indexing
service's /index endpoint.

Run with:
  uvicorn main:app --host 0.0.0.0 --port 7860
"""
import os

import httpx
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

INDEXING_SERVICE_URL = os.getenv("INDEXING_SERVICE_URL", "http://rag-indexing.orfeo-rag.svc.cluster.local:8001",)
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".md", ".txt"}

app = FastAPI(title="Document Indexing")

@app.get("/", response_class=HTMLResponse)
def index_page():
    with open("static/index.html", "r") as f:
        return f.read()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "message": (
                    f"Unsupported file type '{ext}'. Allowed: "
                    + ", ".join(sorted(ALLOWED_EXTENSIONS))
                ),
            },
        )

    contents = await file.read()

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{INDEXING_SERVICE_URL}/index",
                files={"file": (file.filename, contents)},
            )
    except httpx.RequestError as e:
        return JSONResponse(
            status_code=502,
            content={"ok": False, "message": f"Could not reach indexing service: {e}"},
        )

    if resp.status_code == 200:
        data = resp.json()
        return {
            "ok": True,
            "message": (
                f"Indexed '{data.get('filename', file.filename)}' — "
                f"{data.get('documents_written', '?')} chunks written."
            ),
        }
    else:
        return JSONResponse(
            status_code=resp.status_code,
            content={"ok": False, "message": f"Error ({resp.status_code}): {resp.text}"},
        )

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)