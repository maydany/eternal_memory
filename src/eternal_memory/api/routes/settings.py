"""
Settings API Routes

Endpoints for configuration and API key management.
"""

import os
from pathlib import Path
from typing import Optional

import aiofiles
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

CONFIG_PATH = Path.cwd() / "user_memory" / "config" / "memory_config.yaml"
SYSTEM_PROMPT_PATH = Path.cwd() / "setting" / "system_prompt.txt"


class LLMSettings(BaseModel):
    """LLM configuration."""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None


class AppSettings(BaseModel):
    """Application settings."""
    llm: LLMSettings
    system_prompt: Optional[str] = None


@router.get("/")
async def get_settings():
    """
    Get current application settings.
    
    Returns settings from config file and environment.
    Note: API keys are masked for security (showing first/last 4 chars).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    api_key_masked = None
    
    # Mask API key: show first 4 and last 4 characters
    if api_key and len(api_key) > 8:
        api_key_masked = f"{api_key[:4]}...{api_key[-4:]}"
    elif api_key:
        api_key_masked = "****"
    
    settings = {
        "llm": {
            "provider": "openai",
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "api_key_set": bool(api_key),
            "api_key_masked": api_key_masked,
        },
        "system_prompt": None,
    }
    
    if CONFIG_PATH.exists():
        try:
            async with aiofiles.open(CONFIG_PATH, "r") as f:
                content = await f.read()
            config = yaml.safe_load(content) or {}
            
            if "llm" in config:
                settings["llm"]["provider"] = config["llm"].get("provider", "openai")
                settings["llm"]["model"] = config["llm"].get("model", "gpt-4o-mini")
        except Exception:
            pass
    
    # Load system prompt from dedicated file
    if SYSTEM_PROMPT_PATH.exists():
        try:
            async with aiofiles.open(SYSTEM_PROMPT_PATH, "r") as f:
                settings["system_prompt"] = await f.read()
        except Exception:
            pass
    
    return settings


@router.post("/api-key")
async def set_api_key(provider: str, api_key: str):
    """
    Set the API key for an LLM provider.
    
    Note: For security, the key is stored in environment
    and should be persisted via .env or system keychain.
    """
    if provider.lower() == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
        
        # Also save to .env file for persistence
        env_path = Path.cwd() / "setting" / ".env"
        env_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read existing .env
        existing = {}
        if env_path.exists():
            async with aiofiles.open(env_path, "r") as f:
                for line in (await f.read()).split("\n"):
                    if "=" in line:
                        k, v = line.split("=", 1)
                        existing[k.strip()] = v.strip()
        
        # Update key
        existing["OPENAI_API_KEY"] = api_key
        
        # Write back
        async with aiofiles.open(env_path, "w") as f:
            await f.write("\n".join(f"{k}={v}" for k, v in existing.items()))
        
        # Set secure permissions
        os.chmod(env_path, 0o600)
        
        return {"success": True, "message": "API key saved"}
    
    raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

@router.delete("/api-key")
async def delete_api_key(provider: str):
    """
    Delete the API key for an LLM provider.
    
    Removes the key from both environment and .env file.
    """
    if provider.lower() == "openai":
        # Remove from environment
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        # Remove from .env file
        env_path = Path.cwd() / "setting" / ".env"
        if env_path.exists():
            existing = {}
            async with aiofiles.open(env_path, "r") as f:
                for line in (await f.read()).split("\n"):
                    if "=" in line and line.strip():
                        k, v = line.split("=", 1)
                        # Keep all keys except OPENAI_API_KEY
                        if k.strip() != "OPENAI_API_KEY":
                            existing[k.strip()] = v.strip()
            
            # Write back without the API key
            async with aiofiles.open(env_path, "w") as f:
                if existing:
                    await f.write("\n".join(f"{k}={v}" for k, v in existing.items()))
                else:
                    # If no keys left, write empty file
                    await f.write("")
        
        return {"success": True, "message": "API key deleted"}
    
    raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


@router.post("/test-connection")
async def test_connection():
    """
    Test the connection to the configured LLM provider.
    
    Makes a simple API call to verify the API key is valid.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return {"success": False, "error": "API key not set"}
    
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=api_key)
        response = await client.models.list()
        
        return {
            "success": True,
            "message": "Connection successful",
            "models_available": len(response.data),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.put("/system-prompt")
async def update_system_prompt(prompt: str):
    """
    Update the system prompt for conversations.
    
    Saves to setting/system_prompt.txt (not tracked by Git).
    """
    # Create setting directory if it doesn't exist
    SYSTEM_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Save system prompt to dedicated file
    async with aiofiles.open(SYSTEM_PROMPT_PATH, "w") as f:
        await f.write(prompt)
    
    # Set secure permissions
    os.chmod(SYSTEM_PROMPT_PATH, 0o600)
    
    return {"success": True, "message": "System prompt updated"}


@router.get("/models")
async def get_available_models(provider: str = "openai"):
    """
    Get available models from the configured LLM provider.
    
    Fetches the list dynamically from the provider's API.
    """
    if provider.lower() == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            return {
                "success": False,
                "error": "API key not configured",
                "models": [],
            }
        
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=api_key)
            response = await client.models.list()
            
            # Filter and categorize models
            chat_models = []
            embedding_models = []
            
            for model in response.data:
                model_id = model.id
                # Filter for commonly used chat models
                if any(prefix in model_id for prefix in ['gpt-4', 'gpt-3.5', 'o1', 'o3']):
                    if 'embedding' not in model_id and 'audio' not in model_id:
                        chat_models.append({
                            "id": model_id,
                            "name": model_id,
                            "owned_by": model.owned_by,
                        })
                elif 'embedding' in model_id:
                    embedding_models.append({
                        "id": model_id,
                        "name": model_id,
                        "owned_by": model.owned_by,
                    })
            
            # Sort by name
            chat_models.sort(key=lambda x: x["id"], reverse=True)
            embedding_models.sort(key=lambda x: x["id"], reverse=True)
            
            return {
                "success": True,
                "provider": "openai",
                "chat_models": chat_models,
                "embedding_models": embedding_models,
                "total": len(chat_models) + len(embedding_models),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "models": [],
            }
    
    # Fallback for other providers (not implemented yet)
    return {
        "success": False,
        "error": f"Provider '{provider}' not supported yet",
        "models": [],
    }


@router.put("/model")
async def set_model(
    model: Optional[str] = None,
    chat_model: Optional[str] = None,
    memory_model: Optional[str] = None,
    supersede_model: Optional[str] = None,
    use_llm_importance: Optional[bool] = None,
    use_memory_supersede: Optional[bool] = None,
    use_semantic_triples: Optional[bool] = None,
    triple_extraction_immediate: Optional[bool] = None,
    triple_extraction_interval_minutes: Optional[int] = None,
):
    """
    Set the selected model(s) for the LLM provider.
    
    Args:
        model: Legacy single model (for backwards compatibility)
        chat_model: Model for conversations and reasoning
        memory_model: Model for importance rating (lightweight)
        supersede_model: Model for contradiction detection (MemGPT-style)
        use_llm_importance: Whether to use LLM for importance rating
        use_memory_supersede: Whether to detect and supersede contradicting memories
        use_semantic_triples: Whether to extract entity-level triples for precise updates
        triple_extraction_immediate: True = extract triples immediately, False = lazy batch
        triple_extraction_interval_minutes: Interval for batch extraction (1, 5, 10, 30)
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing config
    config = {}
    if CONFIG_PATH.exists():
        async with aiofiles.open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(await f.read()) or {}
    
    # Update models
    if "llm" not in config:
        config["llm"] = {}
    
    if model is not None:
        config["llm"]["model"] = model
        os.environ["OPENAI_MODEL"] = model
    
    if chat_model is not None:
        config["llm"]["chat_model"] = chat_model
    
    if memory_model is not None:
        config["llm"]["memory_model"] = memory_model
    
    if supersede_model is not None:
        config["llm"]["supersede_model"] = supersede_model
    
    if use_llm_importance is not None:
        config["llm"]["use_llm_importance"] = use_llm_importance
    
    if use_memory_supersede is not None:
        config["llm"]["use_memory_supersede"] = use_memory_supersede
    
    if use_semantic_triples is not None:
        config["llm"]["use_semantic_triples"] = use_semantic_triples
    
    if triple_extraction_immediate is not None:
        config["llm"]["triple_extraction_immediate"] = triple_extraction_immediate
    
    if triple_extraction_interval_minutes is not None:
        # Validate allowed values
        allowed_intervals = [1, 5, 10, 30]
        if triple_extraction_interval_minutes not in allowed_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"triple_extraction_interval_minutes must be one of {allowed_intervals}"
            )
        config["llm"]["triple_extraction_interval_minutes"] = triple_extraction_interval_minutes
    
    # Save
    async with aiofiles.open(CONFIG_PATH, "w") as f:
        await f.write(yaml.dump(config, allow_unicode=True))
    
    return {
        "success": True,
        "message": "Model settings updated",
        "settings": config["llm"],
    }


@router.get("/model-config")
async def get_model_config():
    """
    Get current model configuration for chat, memory, and supersede.
    """
    settings = {
        "model": "gpt-4o-mini",
        "chat_model": None,
        "memory_model": "gpt-4o-mini",
        "supersede_model": "gpt-4o-mini",
        "use_llm_importance": False,
        "use_memory_supersede": False,
        "use_semantic_triples": False,
        "triple_extraction_immediate": True,
        "triple_extraction_interval_minutes": 5,
    }
    
    if CONFIG_PATH.exists():
        try:
            async with aiofiles.open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(await f.read()) or {}
            
            if "llm" in config:
                settings["model"] = config["llm"].get("model", "gpt-4o-mini")
                settings["chat_model"] = config["llm"].get("chat_model")
                settings["memory_model"] = config["llm"].get("memory_model", "gpt-4o-mini")
                settings["supersede_model"] = config["llm"].get("supersede_model", "gpt-4o-mini")
                settings["use_llm_importance"] = config["llm"].get("use_llm_importance", False)
                settings["use_memory_supersede"] = config["llm"].get("use_memory_supersede", False)
                settings["use_semantic_triples"] = config["llm"].get("use_semantic_triples", False)
                settings["triple_extraction_immediate"] = config["llm"].get("triple_extraction_immediate", True)
                settings["triple_extraction_interval_minutes"] = config["llm"].get("triple_extraction_interval_minutes", 5)
        except Exception:
            pass
    
    # Compute effective models
    settings["effective_chat_model"] = settings["chat_model"] or settings["model"]
    settings["effective_memory_model"] = settings["memory_model"]
    settings["effective_supersede_model"] = settings["supersede_model"]
    
    return settings


@router.get("/buffer")
async def get_buffer_settings():
    """
    Get current buffer/flush settings.
    """
    settings = {
        "flush_threshold_tokens": 4000,  # Default
        "auto_flush_enabled": True,
    }
    
    if CONFIG_PATH.exists():
        try:
            async with aiofiles.open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(await f.read()) or {}
            
            if "buffer" in config:
                settings["flush_threshold_tokens"] = config["buffer"].get(
                    "flush_threshold_tokens", 4000
                )
                settings["auto_flush_enabled"] = config["buffer"].get(
                    "auto_flush_enabled", True
                )
        except Exception:
            pass
    
    return settings


@router.put("/buffer")
async def update_buffer_settings(
    flush_threshold_tokens: Optional[int] = None,
    auto_flush_enabled: Optional[bool] = None,
):
    """
    Update buffer/flush settings.
    
    Args:
        flush_threshold_tokens: Token threshold before auto-flush (1000-10000)
        auto_flush_enabled: Whether to auto-flush on threshold
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing config
    config = {}
    if CONFIG_PATH.exists():
        async with aiofiles.open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(await f.read()) or {}
    
    # Update buffer settings
    if "buffer" not in config:
        config["buffer"] = {}
    
    if flush_threshold_tokens is not None:
        # Validate range
        if not 1000 <= flush_threshold_tokens <= 10000:
            raise HTTPException(
                status_code=400,
                detail="flush_threshold_tokens must be between 1000 and 10000"
            )
        config["buffer"]["flush_threshold_tokens"] = flush_threshold_tokens
    
    if auto_flush_enabled is not None:
        config["buffer"]["auto_flush_enabled"] = auto_flush_enabled
    
    # Save
    async with aiofiles.open(CONFIG_PATH, "w") as f:
        await f.write(yaml.dump(config, allow_unicode=True))
    
    return {
        "success": True,
        "message": "Buffer settings updated",
        "settings": config["buffer"],
    }


@router.get("/scoring")
async def get_scoring_settings():
    """
    Get current memory scoring settings.
    
    Returns the α weights and decay factor for the Generative Agents-style
    retrieval scoring formula.
    """
    settings = {
        "alpha_relevance": 1.0,
        "alpha_recency": 1.0,
        "alpha_importance": 1.0,
        "recency_decay_factor": 0.995,
        "min_relevance_threshold": 0.3,
    }
    
    if CONFIG_PATH.exists():
        try:
            async with aiofiles.open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(await f.read()) or {}
            
            if "scoring" in config:
                settings["alpha_relevance"] = config["scoring"].get(
                    "alpha_relevance", 1.0
                )
                settings["alpha_recency"] = config["scoring"].get(
                    "alpha_recency", 1.0
                )
                settings["alpha_importance"] = config["scoring"].get(
                    "alpha_importance", 1.0
                )
                settings["recency_decay_factor"] = config["scoring"].get(
                    "recency_decay_factor", 0.995
                )
                settings["min_relevance_threshold"] = config["scoring"].get(
                    "min_relevance_threshold", 0.3
                )
        except Exception:
            pass
    
    return settings


@router.put("/scoring")
async def update_scoring_settings(
    alpha_relevance: Optional[float] = None,
    alpha_recency: Optional[float] = None,
    alpha_importance: Optional[float] = None,
    recency_decay_factor: Optional[float] = None,
    min_relevance_threshold: Optional[float] = None,
):
    """
    Update memory scoring settings.
    
    Based on Generative Agents (Park et al., 2023):
    Score = α_relevance × Relevance + α_recency × Recency + α_importance × Importance
    
    Args:
        alpha_relevance: Weight for semantic similarity (0.0-3.0)
        alpha_recency: Weight for time-based decay (0.0-3.0)
        alpha_importance: Weight for memory importance (0.0-3.0)
        recency_decay_factor: Decay per hour (0.9-0.999)
        min_relevance_threshold: Minimum relevance to include (0.0-1.0)
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing config
    config = {}
    if CONFIG_PATH.exists():
        async with aiofiles.open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(await f.read()) or {}
    
    # Update scoring settings
    if "scoring" not in config:
        config["scoring"] = {}
    
    if alpha_relevance is not None:
        if not 0.0 <= alpha_relevance <= 3.0:
            raise HTTPException(
                status_code=400,
                detail="alpha_relevance must be between 0.0 and 3.0"
            )
        config["scoring"]["alpha_relevance"] = alpha_relevance
    
    if alpha_recency is not None:
        if not 0.0 <= alpha_recency <= 3.0:
            raise HTTPException(
                status_code=400,
                detail="alpha_recency must be between 0.0 and 3.0"
            )
        config["scoring"]["alpha_recency"] = alpha_recency
    
    if alpha_importance is not None:
        if not 0.0 <= alpha_importance <= 3.0:
            raise HTTPException(
                status_code=400,
                detail="alpha_importance must be between 0.0 and 3.0"
            )
        config["scoring"]["alpha_importance"] = alpha_importance
    
    if recency_decay_factor is not None:
        if not 0.9 <= recency_decay_factor <= 0.999:
            raise HTTPException(
                status_code=400,
                detail="recency_decay_factor must be between 0.9 and 0.999"
            )
        config["scoring"]["recency_decay_factor"] = recency_decay_factor
    
    if min_relevance_threshold is not None:
        if not 0.0 <= min_relevance_threshold <= 1.0:
            raise HTTPException(
                status_code=400,
                detail="min_relevance_threshold must be between 0.0 and 1.0"
            )
        config["scoring"]["min_relevance_threshold"] = min_relevance_threshold
    
    # Save
    async with aiofiles.open(CONFIG_PATH, "w") as f:
        await f.write(yaml.dump(config, allow_unicode=True))
    
    return {
        "success": True,
        "message": "Scoring settings updated",
        "settings": config["scoring"],
    }
