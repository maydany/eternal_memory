"""
OpenAI embedding provider implementation.
"""

from typing import List, Optional
from openai import AsyncOpenAI

from .base import EmbeddingProvider, EmbeddingError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider using text-embedding-ada-002.
    
    Supports batch embedding natively through OpenAI's API.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "text-embedding-ada-002",
    ):
        """
        Initialize OpenAI embedding provider.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: Optional base URL for OpenAI-compatible APIs
            model: Embedding model name (default: text-embedding-ada-002)
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        
        # Model dimensions
        self._dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
    
    async def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using OpenAI's batch API.
        
        OpenAI natively supports batch embedding by passing a list
        of strings to the input parameter.
        """
        if not texts:
            return []
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,  # OpenAI accepts list directly
            )
            
            # Extract embeddings in order
            return [item.embedding for item in response.data]
            
        except Exception as e:
            raise EmbeddingError(f"OpenAI embedding failed: {e}") from e
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for the current model."""
        return self._dimensions.get(self.model, 1536)
    
    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model
