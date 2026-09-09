from pathlib import Path
import torch
from transformers import CLIPModel, CLIPProcessor

from openai import OpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse

from sem_rag.config.settings import VLLM
from sem_rag.utils.image import encode_image, load_image_CLIP


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


class CLIPEmbedder:
    """Generate image embeddings using CLIP."""

    MODEL_NAME = "openai/clip-vit-base-patch32"

    def __init__(self):
        """Initialize the CLIP model and processor."""

        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")

        self.processor = CLIPProcessor.from_pretrained(self.MODEL_NAME)
        self.model = CLIPModel.from_pretrained(self.MODEL_NAME)

        self.model.to(self.device)
        self.model.eval()

    def embed_image(self, path: Path) -> list[float]:
        """Generate an embedding for a grayscale SEM image.

        Args:
            path: Path to the `.npy` image file.

        Returns:
            The normalized CLIP image embedding.
        """
        image = load_image_CLIP(path)

        inputs = self.processor(
            images=image,
            return_tensors="pt",
        )

        inputs = {
            key: value.to(self.device)
            for key, value in inputs.items()
        }

        with torch.no_grad():
            vision_output = self.model.vision_model(**inputs)
    
            pooled_output = vision_output.pooler_output
    
            embedding = self.model.visual_projection(pooled_output)

        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        return embedding.squeeze(0).cpu().tolist()

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding for a text query using CLIP.

        Args:
            text: Text query to embed.

        Returns:
            The normalized CLIP text embedding.
        """
        inputs = self.processor(
            text=[text],
            return_tensors="pt",
            padding=True,
        )

        inputs = {key: value.to(self.device) for key, value in inputs.items()}

        with torch.no_grad():
            # Encode the text using CLIP's text encoder
            text_output = self.model.text_model(**inputs)
            # Extract the pooled representation of the text tokens
            pooled_output = text_output.pooler_output
            # Project the pooled representation into CLIP's shared image-text embedding space
            embedding = self.model.text_projection(pooled_output)

        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        return embedding.squeeze(0).cpu().tolist()
