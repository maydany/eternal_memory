"""
Google Gemini embedding provider implementation.
"""

import asyncio
from typing import List, Optional

from .base import EmbeddingProvider, EmbeddingError


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Google Gemini embedding provider.
    
    Uses asyncio.gather for batch processing since Gemini API
    processes embeddings individually.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "models/embedding-001",
    ):
        """
        Initialize Gemini embedding provider.
        
        Args:
            api_key: Google AI API key (defaults to GOOGLE_API_KEY env var)
            model: Embedding model name (default: models/embedding-001)
        """
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai package required for Gemini provider. "
                "Install with: pip install google-generativeai"
            )
        
        self.genai = genai
        
        # Configure API key
        if api_key:
            genai.configure(api_key=api_key)
        
        self.model = model
        
        # Gemini embedding-001 produces 768-dimensional vectors
        self._dimension = 768
    
    async def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using Gemini API with asyncio.gather.
        
        Gemini doesn't have native batch support, so we use
        asyncio.gather to process multiple texts concurrently.
        """
        if not texts:
            return []
        
        try:
            # Create coroutines for each text
            tasks = [
                self._embed_single(text) for text in texts
            ]
            
            # Execute all tasks concurrently
            embeddings = await asyncio.gather(*tasks)
            
            return embeddings
            
        except Exception as e:
            raise EmbeddingError(f"Gemini embedding failed: {e}") from e
    
    async def _embed_single(self, text: str) -> List[float]:
        """
        Embed a single text using Gemini API.
        
        Note: google-generativeai is synchronous, so we use
        asyncio.to_thread to avoid blocking.
        """
        def _sync_embed():
            result = self.genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
        
        # Run sync function in thread pool
        embedding = await asyncio.to_thread(_sync_embed)
        return embedding
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for Gemini."""
        return self._dimension
    
    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model
