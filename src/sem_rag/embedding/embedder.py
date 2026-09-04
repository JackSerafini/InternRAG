from pathlib import Path

from openai import OpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse

from sem_rag.config.settings import VLLM
from sem_rag.utils.image import encode_image


INSTRUCTION = "Represent the user's input."


class QwenEmbedder:
    """Generate text and image embeddings using Qwen3-VL-Embedding."""

    def __init__(self):
        """Initialize the Qwen embedding client and model."""

        self.client = OpenAI(base_url=VLLM.API_URL, api_key=VLLM.API_KEY)

        self.model = next(
            model
            for model in self.client.models.list().data
            if model.id == VLLM.EMBEDDING_MODEL
        ).id

    def embed_image(self, path: Path) -> list[float]:
        """Generate an embedding for an image.

        Args:
            path: Path to the image file.

        Returns:
            The image embedding as a list of floats.
        """
        messages = [
            {"role": "system", "content": [{"type": "text", "text": INSTRUCTION}]},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": encode_image(path)}},
                {"type": "text", "text": ""}
            ]},
            {"role": "assistant", "content": [{"type": "text", "text": ""}]},
        ]

        response: CreateEmbeddingResponse = self.client.post(
            "/embeddings",
            cast_to=CreateEmbeddingResponse,
            body={
                "messages": messages,
                "model": self.model,
                "encoding_format": "float",
                "continue_final_message": True,
                "add_special_tokens": True,
            },
        )

        return response.data[0].embedding
