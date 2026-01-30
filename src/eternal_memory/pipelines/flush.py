"""
Flush Pipeline

Analyzes a buffer of messages to extract durable memories before compaction/deletion.
"""

from datetime import datetime
from typing import List, Optional

from eternal_memory.database.repository import MemoryRepository
from eternal_memory.llm.client import LLMClient
from eternal_memory.models.memory_item import MemoryItem
from eternal_memory.pipelines.memorize import MemorizePipeline
from eternal_memory.vault.markdown_vault import MarkdownVault


class FlushPipeline:
    """
    Pipeline for flushing memory buffer.
    
    1. Takes a list of messages (conversation history)
    2. Uses LLM to extract "Enduring Facts"
    3. Memorizes them using the standard MemorizePipeline
    """
    
    def __init__(
        self,
        repository: MemoryRepository,
        llm_client: LLMClient,
        vault: MarkdownVault,
        memorize_pipeline: MemorizePipeline,
    ):
        self.repository = repository
        self.llm = llm_client
        self.vault = vault
        self.memorize_pipeline = memorize_pipeline
        
    async def execute(self, messages: List[dict]) -> List[MemoryItem]:
        """
        Execute flush pipeline.
        
        Args:
            messages: List of dicts with 'role' and 'content' keys
            
        Returns:
            List of created MemoryItems
        """
        if not messages:
            return []
            
        # 1. Prepare context for LLM
        transcript = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
        
        # 2. Prompt LLM for extraction
        prompt = f"""Analyze this conversation transcript and extract specific, enduring facts about the user that should be committed to long-term memory.
Focus on user preferences, biographical details, and relationships.
Do NOT extract trivial details or current context that will become irrelevant (like "user wants to write code").

Transcript:
{transcript}

Respond with a list of facts, one per line.
If there are no enduring facts to save, respond with "NONE".
"""
        
        response = await self.llm.complete(prompt)
        
        created_items = []
        
        # 3. Process response
        if response and response.strip().upper() != "NONE":
            for line in response.split("\n"):
                line = line.strip()
                if not line or line.upper() == "NONE":
                    continue
                    
                # Clean up bullets if present
                if line.startswith("- "):
                    line = line[2:]
                
                # Use standard memorize pipeline to store this fact
                # This handles categorization, embedding, and saving
                item = await self.memorize_pipeline.store_single_memory(
                    content=line,
                    metadata={"source": "memory_flush", "timestamp": datetime.now().isoformat()}
                )
                created_items.append(item)
                
        return created_items
