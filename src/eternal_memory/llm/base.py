"""
Base classes for LLM and Embedding providers.

This module defines abstract interfaces that allow supporting
multiple LLM providers (OpenAI, Gemini, etc.) through the adapter pattern.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.
    
    Implementations must provide batch embedding functionality
    for efficient API usage.
    """
    
    @abstractmethod
    async def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single API call.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors in the same order as input texts
            
        Raises:
            EmbeddingError: If the embedding API fails
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this provider.
        
        Returns:
            Embedding vector dimension (e.g., 1536 for OpenAI ada-002)
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the name of the embedding model being used.
        
        Returns:
            Model name string
        """
        pass


class EmbeddingError(Exception):
    """Exception raised when embedding generation fails."""
    pass
