"""
Minimal upload UI for the indexing service.

This is intentionally bare-bones: a single file-upload widget that POSTs
to the indexing service's /index endpoint.

Run with:
  python upload_ui.py
"""
import os

import gradio as gr
import requests

INDEXING_SERVICE_URL = os.getenv("INDEXING_SERVICE_URL", "http://rag-indexing.orfeo-rag.svc.cluster.local:8001")

def upload_file(file_path):
    if file_path is None:
        return "No file selected."

    filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        try:
            resp = requests.post(
                f"{INDEXING_SERVICE_URL}/index",
                files={"file": (filename, f)},
                timeout=300,  # docling parsing can be slow on large files
            )
        except requests.RequestException as e:
            return f"Could not reach indexing service: {e}"

    if resp.status_code == 200:
        data = resp.json()
        return f"✅ Indexed '{data['filename']}' — {data.get('documents_written', '?')} chunks written."
    else:
        return f"❌ Error ({resp.status_code}): {resp.text}"

with gr.Blocks(title="Document Indexing") as demo:
    gr.Markdown("# Document Indexing\nUpload a document to add it to the RAG knowledge base.")
    file_input = gr.File(label="Select a document", file_types=[".pdf", ".docx", ".pptx", ".html", ".md", ".txt"])
    upload_btn = gr.Button("Index Document", variant="primary")
    output = gr.Textbox(label="Status", interactive=False)

    upload_btn.click(fn=upload_file, inputs=file_input, outputs=output)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)