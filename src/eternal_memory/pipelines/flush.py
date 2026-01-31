"""
Flush Pipeline

Analyzes a buffer of messages to extract durable memories before compaction/deletion.
Also extracts immediate user insights for USER.md (near-real-time user profiling).
"""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
import logging

from eternal_memory.database.repository import MemoryRepository
from eternal_memory.llm.client import LLMClient
from eternal_memory.models.memory_item import MemoryItem
from eternal_memory.pipelines.memorize import MemorizePipeline
from eternal_memory.vault.markdown_vault import MarkdownVault

if TYPE_CHECKING:
    from eternal_memory.agent.user_model import UserModel

logger = logging.getLogger("eternal_memory.pipelines.flush")


class FlushPipeline:
    """
    Pipeline for flushing memory buffer.
    
    1. Takes a list of messages (conversation history)
    2. Uses LLM to extract "Enduring Facts"
    3. Memorizes them using the standard MemorizePipeline
    4. Extracts immediate user insights to USER.md (near-real-time)
    
    The user insight extraction uses a lower quality threshold than
    daily profile_reflection to capture facts "in the moment".
    """
    
    # Lower thresholds for immediate capture
    # (daily profile_reflection will validate/strengthen these later)
    IMMEDIATE_CONFIDENCE_THRESHOLD = 0.6
    IMMEDIATE_EVIDENCE_THRESHOLD = 1
    
    def __init__(
        self,
        repository: MemoryRepository,
        llm_client: LLMClient,
        vault: MarkdownVault,
        memorize_pipeline: MemorizePipeline,
        user_model: Optional["UserModel"] = None,
    ):
        self.repository = repository
        self.llm = llm_client
        self.vault = vault
        self.memorize_pipeline = memorize_pipeline
        self.user_model = user_model
        
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
        
        # 4. Extract immediate user insights to USER.md
        if self.user_model:
            await self._extract_immediate_user_insights(transcript)
        
        return created_items
    
    async def _extract_immediate_user_insights(self, transcript: str) -> int:
        """
        Extract immediate user insights from conversation and add to USER.md.
        
        Uses a lower quality threshold for "in the moment" capture.
        The daily profile_reflection job will validate and strengthen these later.
        
        Args:
            transcript: Formatted conversation transcript
            
        Returns:
            Number of insights added
        """
        if not self.user_model:
            return 0
        
        # Prompt for immediate user facts
        prompt = f"""Analyze this conversation and extract IMMEDIATE facts about the user 
that should be recorded in their profile for future personalization.

Focus on:
- Explicit statements: "I am...", "I prefer...", "I work as...", "I don't like..."
- Dietary restrictions, accessibility needs, or constraints
- Timezone, language preferences, communication style
- Current projects or active contexts

Examples of what to capture:
- "I'm vegan" → Established Preferences: User follows a vegan diet
- "I work at Samsung" → Core Identity: Works at Samsung
- "I use TypeScript for everything" → Technical Context: Prefers TypeScript

Conversation:
{transcript}

Output JSON with this structure:
{{
  "insights": [
    {{
      "section": "Established Preferences",
      "content": "User follows a vegan diet",
      "confidence": 0.95,
      "evidence_count": 1,
      "source_quote": "I'm vegan"
    }}
  ]
}}

Valid sections: "Core Identity", "Established Preferences", "Work Patterns", 
"Communication Style", "Technical Context", "Constraints"

If no significant user facts found, return: {{"insights": []}}
Only include facts explicitly stated or strongly implied by the user."""

        try:
            response = await self.llm.complete(prompt, response_format="json_object")
            insights = response.get("insights", [])
            
            if not insights:
                logger.debug("No immediate user insights found in conversation")
                return 0
            
            # Filter by immediate threshold (lower than daily reflection)
            filtered_insights = []
            for insight in insights:
                confidence = insight.get("confidence", 0)
                evidence = insight.get("evidence_count", 0)
                
                # Use lower thresholds for immediate capture
                if confidence >= self.IMMEDIATE_CONFIDENCE_THRESHOLD:
                    # Override evidence_count to 1 for immediate capture
                    # (will be aggregated by daily profile_reflection)
                    insight["evidence_count"] = max(evidence, 1)
                    filtered_insights.append(insight)
            
            if not filtered_insights:
                return 0
            
            # Add to USER.md with adjusted thresholds
            # We need to temporarily lower the UserModel thresholds
            original_min_confidence = self.user_model.MIN_CONFIDENCE
            original_min_evidence = self.user_model.MIN_EVIDENCE
            
            try:
                # Temporarily lower thresholds for immediate capture
                self.user_model.MIN_CONFIDENCE = self.IMMEDIATE_CONFIDENCE_THRESHOLD
                self.user_model.MIN_EVIDENCE = self.IMMEDIATE_EVIDENCE_THRESHOLD
                
                added = await self.user_model.batch_update(filtered_insights)
                
                if added > 0:
                    logger.info(f"🧠 Immediate capture: added {added} user insights to USER.md")
                
                return added
                
            finally:
                # Restore original thresholds
                self.user_model.MIN_CONFIDENCE = original_min_confidence
                self.user_model.MIN_EVIDENCE = original_min_evidence
                
        except Exception as e:
            logger.error(f"Failed to extract immediate user insights: {e}")
            return 0
