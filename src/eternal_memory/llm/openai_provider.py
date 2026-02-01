"""
OpenAI embedding provider implementation.
"""

from typing import List, Optional
from openai import AsyncOpenAI

from .base import EmbeddingProvider, EmbeddingError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider using text-embedding-3-large with Matryoshka dimension reduction.
    
    Supports batch embedding natively through OpenAI's API.
    Using embedding-3-large for improved multilingual performance (MIRACL: 54.9%).
    
    Note: We use dimensions=1536 for pgvector compatibility while keeping
    embedding-3-large's superior cross-lingual performance.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "text-embedding-3-large",
        dimensions: Optional[int] = 1536,  # Matryoshka: reduce 3072 → 1536 for pgvector
    ):
        """
        Initialize OpenAI embedding provider.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: Optional base URL for OpenAI-compatible APIs
            model: Embedding model name (default: text-embedding-3-large)
            dimensions: Output dimension (for Matryoshka models like embedding-3-*)
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.dimensions = dimensions
        
        # Native model dimensions (before reduction)
        self._native_dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
    
    async def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using OpenAI's batch API.
        
        OpenAI natively supports batch embedding by passing a list
        of strings to the input parameter.
        
        Uses Matryoshka dimension reduction if dimensions is specified.
        """
        if not texts:
            return []
        
        try:
            # Build request kwargs
            kwargs = {
                "model": self.model,
                "input": texts,
            }
            
            # Add dimensions parameter for Matryoshka models
            if self.dimensions and self.model.startswith("text-embedding-3"):
                kwargs["dimensions"] = self.dimensions
            
            response = await self.client.embeddings.create(**kwargs)
            
            # Extract embeddings in order
            return [item.embedding for item in response.data]
            
        except Exception as e:
            raise EmbeddingError(f"OpenAI embedding failed: {e}") from e
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for the current model.
        
        Returns the reduced dimension if Matryoshka is used.
        """
        if self.dimensions and self.model.startswith("text-embedding-3"):
            return self.dimensions
        return self._native_dimensions.get(self.model, 1536)
    
    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model

