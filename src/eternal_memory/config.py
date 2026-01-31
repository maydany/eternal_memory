"""
Configuration

Loads and manages system configuration from memory_config.yaml
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path.cwd() / "setting" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed


class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    host: str = "localhost"
    port: int = 5432
    name: str = "eternal_memory"
    user: Optional[str] = None
    password: Optional[str] = None
    
    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        if self.user and self.password:
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        return f"postgresql://{self.host}:{self.port}/{self.name}"


class RetentionConfig(BaseModel):
    """Memory retention policy configuration."""
    stale_days_threshold: int = 30
    archive_low_importance: bool = True
    importance_threshold: float = 0.3


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""
    model: str = "text-embedding-ada-002"
    dimension: int = 1536


class ConsolidationConfig(BaseModel):
    """Consolidation schedule configuration."""
    enabled: bool = True
    interval_hours: int = 24


class ScoringConfig(BaseModel):
    """Memory scoring configuration based on Generative Agents (Park et al., 2023).
    
    Retrieval score = α_relevance × Relevance + α_recency × Recency + α_importance × Importance
    """
    # Alpha weights for scoring formula
    alpha_relevance: float = 1.0  # Weight for semantic similarity
    alpha_recency: float = 1.0    # Weight for time-based decay
    alpha_importance: float = 1.0 # Weight for memory importance
    
    # Recency decay factor (per hour)
    # 0.995 = Generative Agents default
    # Score decays as: decay_factor^hours_since_access
    recency_decay_factor: float = 0.995
    
    # Minimum relevance threshold for retrieval
    min_relevance_threshold: float = 0.3




class LLMConfig(BaseModel):
    """LLM configuration with dual model support.
    
    - chat_model: Used for conversations and reasoning
    - memory_model: Used for importance rating (lightweight tasks)
    - supersede_model: Used for contradiction/update detection (MemGPT-style)
    """
    # Legacy 'model' field for backwards compatibility
    model: str = "gpt-4o-mini"
    
    # Separate models for different tasks
    chat_model: Optional[str] = None  # Falls back to 'model' if not set
    memory_model: str = "gpt-4o-mini"  # Lightweight, cheaper model for importance rating
    supersede_model: str = "gpt-4o-mini"  # Model for update/contradiction detection
    
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    # Feature toggles
    use_llm_importance: bool = False  # Whether to use LLM for importance rating
    use_memory_supersede: bool = False  # Whether to detect and supersede contradicting memories
    
    def get_chat_model(self) -> str:
        """Get the model to use for chat/reasoning."""
        return self.chat_model or self.model
    
    def get_memory_model(self) -> str:
        """Get the model to use for memory operations (importance rating)."""
        return self.memory_model
    
    def get_supersede_model(self) -> str:
        """Get the model to use for contradiction detection."""
        return self.supersede_model



class BufferConfig(BaseModel):
    """Conversation buffer configuration."""
    flush_threshold_tokens: int = 4000  # OpenClaw default
    auto_flush_enabled: bool = True


class MemoryConfig(BaseModel):
    """Main configuration model."""
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    consolidation: ConsolidationConfig = Field(default_factory=ConsolidationConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    buffer: BufferConfig = Field(default_factory=BufferConfig)



def load_config(config_path: Optional[Path] = None) -> MemoryConfig:
    """
    Load configuration from YAML file.
    
    Falls back to environment variables and defaults.
    """
    if config_path is None:
        config_path = Path.cwd() / "user_memory" / "config" / "memory_config.yaml"
    
    config_data = {}
    
    if config_path.exists():
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}
    
    # Override with environment variables
    if os.getenv("OPENAI_API_KEY"):
        if "llm" not in config_data:
            config_data["llm"] = {}
        config_data["llm"]["api_key"] = os.getenv("OPENAI_API_KEY")
    
    if os.getenv("DATABASE_URL"):
        # Parse database URL if provided
        db_url = os.getenv("DATABASE_URL")
        if "database" not in config_data:
            config_data["database"] = {}
        # Simple parsing - in production use urllib.parse
        if db_url.startswith("postgresql://"):
            config_data["database"]["host"] = "localhost"
            config_data["database"]["name"] = "eternal_memory"
    
    return MemoryConfig(**config_data)
