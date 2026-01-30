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

CONFIG_PATH = Path.home() / ".openclaw" / "config" / "memory_config.yaml"


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
    Note: API keys are masked for security.
    """
    settings = {
        "llm": {
            "provider": "openai",
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "api_key_set": bool(os.getenv("OPENAI_API_KEY")),
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
            
            settings["system_prompt"] = config.get("system_prompt")
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
        env_path = Path.home() / ".openclaw" / ".env"
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
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing config
    config = {}
    if CONFIG_PATH.exists():
        async with aiofiles.open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(await f.read()) or {}
    
    # Update system prompt
    config["system_prompt"] = prompt
    
    # Save
    async with aiofiles.open(CONFIG_PATH, "w") as f:
        await f.write(yaml.dump(config, allow_unicode=True))
    
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
async def set_model(model: str):
    """
    Set the selected model for the LLM provider.
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing config
    config = {}
    if CONFIG_PATH.exists():
        async with aiofiles.open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(await f.read()) or {}
    
    # Update model
    if "llm" not in config:
        config["llm"] = {}
    config["llm"]["model"] = model
    
    # Also update environment variable for immediate use
    os.environ["OPENAI_MODEL"] = model
    
    # Save
    async with aiofiles.open(CONFIG_PATH, "w") as f:
        await f.write(yaml.dump(config, allow_unicode=True))
    
    return {"success": True, "message": f"Model set to {model}"}
