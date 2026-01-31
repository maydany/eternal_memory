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


class LLMConfig(BaseModel):
    """LLM configuration."""
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None


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
