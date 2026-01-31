"""
LLM Client

Handles all LLM interactions including:
- Fact extraction
- Category assignment  
- Query evolution
- Context reasoning
- Summarization
"""

import json
import os
from typing import List, Optional, Callable, Any

from openai import AsyncOpenAI

from eternal_memory.models.memory_item import MemoryType


class LLMClient:
    """
    Client for LLM interactions using OpenAI API.
    
    Supports any OpenAI-compatible API by setting the base URL.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
        usage_callback: Optional[callable] = None,
    ):
        self.model = model
        self.usage_callback = usage_callback
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url,
        )
    
    async def _report_usage(self, response: Any, model_override: str = None):
        """Helper to report token usage via callback."""
        if self.usage_callback and hasattr(response, "usage") and response.usage:
            await self.usage_callback(
                model_override or self.model,
                response.usage.prompt_tokens,
                getattr(response.usage, "completion_tokens", 0),
                response.usage.total_tokens
            )

    async def extract_facts(
        self,
        text: str,
        existing_categories: List[str],
    ) -> List[dict]:
        """
        Extract salient facts from input text.
        
        Returns list of facts with category assignments.
        """
        prompt = f"""Analyze the following input and extract independent memory items.
Focus on FACTS, PREFERENCES, EVENTS, and GOALS.
Ignore trivial chit-chat.

Existing categories: {', '.join(existing_categories) if existing_categories else 'None yet'}

Input: "{text}"

Output Format (JSON array):
[
  {{
    "content": "The extracted fact or memory",
    "type": "fact" | "preference" | "event" | "plan",
    "category_path": "knowledge/topic/subtopic",
    "importance": 0.0 to 1.0
  }}
]

Rules:
- Create new category paths if needed, following the hierarchy: knowledge/, personal/, projects/, etc.
- importance: 1.0 for critical info, 0.5 for normal, 0.1 for minor details
- Extract multiple facts if present
- Return empty array [] if no meaningful facts found

Return ONLY valid JSON array, no other text."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        await self._report_usage(response)
        
        try:
            result = json.loads(response.choices[0].message.content)
            # Handle both {"facts": [...]} and [...] formats
            if isinstance(result, dict):
                return result.get("facts", result.get("items", []))
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, IndexError):
            return []
    
    async def evolve_query(
        self,
        query: str,
        conversation_context: str = "",
    ) -> str:
        """
        Evolve a vague query into a more specific one.
        
        e.g., "그때 거기 어디였지?" → "지난달 출장 갔을 때 묵었던 호텔 이름은?"
        """
        prompt = f"""You are helping to clarify a user's memory retrieval query.
        
Conversation context: {conversation_context or "None"}

User query: "{query}"

If the query is already specific enough, return it as-is.
If the query is vague or uses pronouns/references that need context, rewrite it to be more specific.

Return ONLY the clarified query, nothing else."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        await self._report_usage(response)
        
        return response.choices[0].message.content.strip()
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI's embedding model.
        
        Returns 1536-dimensional vector compatible with ada-002.
        """
        response = await self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=text,
        )
        await self._report_usage(response, model_override="text-embedding-ada-002")
        return response.data[0].embedding
    
    async def reason_from_context(
        self,
        query: str,
        context_items: List[str],
        category_summaries: List[str],
    ) -> str:
        """
        Deep reasoning mode: synthesize answer from context.
        """
        context = "\n".join([f"- {item}" for item in context_items])
        summaries = "\n".join([f"Category: {s}" for s in category_summaries])
        
        prompt = f"""Based on the following memory context, answer the user's query.

Query: "{query}"

Relevant memories:
{context}

Category summaries:
{summaries}

Provide a helpful answer based on the memories above. If the information is insufficient, say so."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        await self._report_usage(response)
        
        return response.choices[0].message.content
    
    async def summarize_category(
        self,
        category_path: str,
        items: List[str],
    ) -> str:
        """
        Generate a summary for a category based on its items.
        """
        items_text = "\n".join([f"- {item}" for item in items])
        
        prompt = f"""Summarize the following memory items belonging to category "{category_path}".

Items:
{items_text}

Create a concise 2-3 sentence summary that captures the key themes and important facts.
This summary will be used as a quick reference for this category."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        await self._report_usage(response)
        
        return response.choices[0].message.content
    
    async def predict_next_intent(
        self,
        current_context: dict,
        recent_patterns: List[str],
    ) -> str:
        """
        Predict user's next intent based on context and patterns.
        """
        context_str = json.dumps(current_context, ensure_ascii=False, indent=2)
        patterns_str = "\n".join([f"- {p}" for p in recent_patterns])
        
        prompt = f"""Based on the current context and past behavioral patterns, predict what the user might need next.

Current context:
{context_str}

Recent patterns:
{patterns_str}

Generate a brief context string (1-2 sentences) that could be helpful for proactively assisting the user.
Focus on actionable predictions, not just observations."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        await self._report_usage(response)
        
        return response.choices[0].message.content
    
    async def suggest_category(
        self,
        fact_content: str,
        candidate_categories: List[str],
    ) -> str:
        """
        Determine the best category path for a fact given some candidates.
        Allows for intelligent fuzzy matching or creating new sub-branches.
        """
        candidates = "\n".join([f"- {c}" for c in candidate_categories])
        
        prompt = f"""You are a memory librarian. Given a fact, determine the most logical category path.
        
Fact: "{fact_content}"

Candidates (Existing Categories):
{candidates if candidates else "None useful found."}

Rules:
1. If an existing category is a perfect or very strong match, use it.
2. If the fact belongs to an existing category but needs a more specific sub-branch, append it: e.g. "knowledge/coding" -> "knowledge/coding/python".
3. If no category fits, create a new one under a standard root:
   - knowledge/ (for general info, facts, data)
   - personal/ (for user's feelings, family, habits, lifestyle)
   - projects/ (for work, code, side projects)
   - timeline/ (for specific ephemeral events)
4. Use English for category names, lowercase, /-separated hierarchy.

Category path (ONLY the path):"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        await self._report_usage(response)
        
        return response.choices[0].message.content.strip().lower()

    async def assign_category(
        self,
        content: str,
        existing_categories: List[str],
    ) -> str:
        """
        Determine the best category for a piece of content.
        """
        categories_str = "\n".join([f"- {c}" for c in existing_categories]) if existing_categories else "None yet"
        
        prompt = f"""Assign a category path to the following content.

Content: "{content}"

Existing categories:
{categories_str}

Rules:
- Use existing category if appropriate
- Create new path if needed (format: top/sub/detail)
- Standard top-level: knowledge/, personal/, projects/, etc.
- Return ONLY the category path, nothing else

Category path:"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        await self._report_usage(response)
        
        return response.choices[0].message.content.strip()

    async def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """
        Generate a straight completion for a prompt.
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        await self._report_usage(response)
        return response.choices[0].message.content

    async def generate_daily_reflection(
        self,
        memory_items: List[str],
        date_str: str,
    ) -> dict:
        """
        Generate a structured daily reflection from the day's memories.
        
        Args:
            memory_items: List of memory content strings from the past 24 hours
            date_str: Date string for the reflection (e.g., "2026-01-31")
            
        Returns:
            Dictionary with keys: summary, key_events, sentiment, insights
        """
        items_text = "\n".join([f"- {item}" for item in memory_items])
        
        prompt = f"""You are a personal memory analyst. Based on the following memories from {date_str}, create a daily reflection.

Memories from today:
{items_text}

Analyze these memories and provide a structured reflection in JSON format:
{{
    "summary": "A 1-2 sentence high-level summary of the day, focusing on what was most significant",
    "key_events": ["List of 3-5 most notable events or facts from today"],
    "sentiment": "overall emotional tone: positive, neutral, or negative",
    "insights": "1-2 sentences about patterns, new discoveries about the user, or actionable observations"
}}

Guidelines:
- Be concise but insightful
- Focus on what would be useful to recall weeks or months later
- If there are recurring themes, note them in insights
- The summary should capture the essence of the day

Return ONLY valid JSON, no other text."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        await self._report_usage(response)
        
        try:
            result = json.loads(response.choices[0].message.content)
            # Ensure all expected keys exist with defaults
            return {
                "summary": result.get("summary", "No summary available."),
                "key_events": result.get("key_events", []),
                "sentiment": result.get("sentiment", "neutral"),
                "insights": result.get("insights", ""),
            }
        except (json.JSONDecodeError, KeyError):
            return {
                "summary": f"Daily reflection for {date_str} (parsing failed).",
                "key_events": [],
                "sentiment": "neutral",
                "insights": "",
            }

    async def generate_weekly_summary(
        self,
        daily_reflections: List[str],
        week_str: str,
    ) -> dict:
        """
        Generate a weekly summary from daily reflections.
        
        Args:
            daily_reflections: List of daily reflection content strings
            week_str: Week identifier (e.g., "2026-W05")
            
        Returns:
            Dictionary with keys: summary, themes, patterns, achievements, advice
        """
        items_text = "\n\n".join([f"Day {i+1}:\n{item}" for i, item in enumerate(daily_reflections)])
        
        prompt = f"""You are a personal memory analyst. Based on the following daily reflections from {week_str}, create a weekly summary.

Daily Reflections:
{items_text}

Analyze these reflections and provide a structured weekly summary in JSON format:
{{
    "summary": "A 2-3 sentence high-level summary of the week's key highlights",
    "themes": ["List of 3-5 major themes or topics that dominated the week"],
    "patterns": "Note any recurring behaviors, habits, or trends observed",
    "achievements": ["List of notable accomplishments or milestones this week"],
    "advice": "1-2 sentences of actionable advice for the coming week based on patterns observed"
}}

Guidelines:
- Synthesize across days, don't just list them
- Look for patterns that span multiple days
- Focus on what would be useful for long-term recall
- The advice should be practical and specific

Return ONLY valid JSON, no other text."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        await self._report_usage(response)
        
        try:
            result = json.loads(response.choices[0].message.content)
            return {
                "summary": result.get("summary", "No summary available."),
                "themes": result.get("themes", []),
                "patterns": result.get("patterns", ""),
                "achievements": result.get("achievements", []),
                "advice": result.get("advice", ""),
            }
        except (json.JSONDecodeError, KeyError):
            return {
                "summary": f"Weekly summary for {week_str} (parsing failed).",
                "themes": [],
                "patterns": "",
                "achievements": [],
                "advice": "",
            }

    async def generate_monthly_summary(
        self,
        weekly_summaries: List[str],
        month_str: str,
    ) -> dict:
        """
        Generate a monthly summary from weekly summaries.
        
        Args:
            weekly_summaries: List of weekly summary content strings
            month_str: Month identifier (e.g., "2026-01")
            
        Returns:
            Dictionary with keys: summary, keywords, trends, growth, goals
        """
        items_text = "\n\n".join([f"Week {i+1}:\n{item}" for i, item in enumerate(weekly_summaries)])
        
        prompt = f"""You are a personal memory analyst. Based on the following weekly summaries from {month_str}, create a monthly summary.

Weekly Summaries:
{items_text}

Analyze these summaries and provide a structured monthly summary in JSON format:
{{
    "summary": "A 3-4 sentence comprehensive summary of the month's journey and key highlights",
    "keywords": ["5-7 keywords that best represent this month"],
    "trends": "Analysis of long-term trends, changes in focus, or evolving interests",
    "growth": "Observations about personal growth, learning, or change during this month",
    "goals": ["2-3 suggested goals or focus areas for the next month based on patterns"]
}}

Guidelines:
- Take a bird's-eye view of the entire month
- Look for evolution and change over the weeks
- Keywords should be specific and meaningful, not generic
- Growth observations should be insightful and actionable
- Goals should flow naturally from observed patterns

Return ONLY valid JSON, no other text."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        await self._report_usage(response)
        
        try:
            result = json.loads(response.choices[0].message.content)
            return {
                "summary": result.get("summary", "No summary available."),
                "keywords": result.get("keywords", []),
                "trends": result.get("trends", ""),
                "growth": result.get("growth", ""),
                "goals": result.get("goals", []),
            }
        except (json.JSONDecodeError, KeyError):
            return {
                "summary": f"Monthly summary for {month_str} (parsing failed).",
                "keywords": [],
                "trends": "",
                "growth": "",
                "goals": [],
            }
