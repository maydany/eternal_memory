"""
Unit Tests for LLM Client

Tests LLM client logic using mocks. Does not require OpenAI API key.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import json


class TestLLMClient:
    """Unit tests for LLMClient."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client for testing."""
        from eternal_memory.llm.client import LLMClient
        
        client = LLMClient(api_key="mock-key", model="gpt-4o-mini")
        client.client = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_extract_facts_returns_structured_data(self, mock_llm_client):
        """Test that extract_facts returns properly structured facts."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "facts": [
                {"content": "User likes coffee", "type": "preference", "importance": 0.8}
            ]
        })
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        
        mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await mock_llm_client.extract_facts("I really love coffee", [])
        
        assert len(result) == 1
        assert result[0]["content"] == "User likes coffee"
        assert result[0]["type"] == "preference"

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_vector(self, mock_llm_client):
        """Test that generate_embedding returns a float vector."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1] * 1536
        
        mock_llm_client.client.embeddings.create = AsyncMock(return_value=mock_response)
        
        result = await mock_llm_client.generate_embedding("test text")
        
        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)

    @pytest.mark.asyncio
    async def test_evolve_query_improves_search_query(self, mock_llm_client):
        """Test that evolve_query generates a better search query."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "What programming languages does the user prefer?"
        mock_response.usage = MagicMock(prompt_tokens=50, completion_tokens=20, total_tokens=70)
        
        mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await mock_llm_client.evolve_query("language")
        
        assert "programming" in result.lower() or "prefer" in result.lower()

    @pytest.mark.asyncio
    async def test_suggest_category_returns_valid_path(self, mock_llm_client):
        """Test that suggest_category returns a valid category path."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "personal/preferences"
        mock_response.usage = MagicMock(prompt_tokens=30, completion_tokens=5, total_tokens=35)
        
        mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await mock_llm_client.suggest_category(
            fact_content="I like tea",
            candidate_categories=["personal/preferences", "knowledge/food"]
        )
        
        # Just verify it returns a path-like string
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_daily_reflection_handles_empty_memories(self, mock_llm_client):
        """Test that daily reflection handles empty input gracefully."""
        # Mock the LLM response for empty case
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"summary": "No activities today.", "key_events": [], "sentiment": "neutral", "insights": ""}'
        mock_response.usage = MagicMock(prompt_tokens=50, completion_tokens=30, total_tokens=80)
        mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await mock_llm_client.generate_daily_reflection([], "2026-01-31")
        
        # Should return default structure
        assert "summary" in result
        assert isinstance(result["key_events"], list)

    @pytest.mark.asyncio
    async def test_generate_weekly_summary_returns_structure(self, mock_llm_client):
        """Test generating a weekly summary."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"summary": "Good week", "themes": ["coding"], "achievements": ["tests"], "patterns": "work", "advice": "rest"}'
        mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Only take week_str as second argument
        result = await mock_llm_client.generate_weekly_summary([], "2026-W05")
        
        assert "summary" in result
        assert "themes" in result
        assert "Good week" in result["summary"]

    @pytest.mark.asyncio
    async def test_generate_monthly_summary_returns_structure(self, mock_llm_client):
        """Test generating a monthly summary."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"summary": "Good month", "keywords": ["growth"], "trends": "upward", "growth": "high", "goals": ["more tests"]}'
        mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await mock_llm_client.generate_monthly_summary([], "2026-01")
        
        assert "summary" in result
        assert "trends" in result
        assert "Good month" in result["summary"]

    @pytest.mark.asyncio
    async def test_reason_from_context_generates_answer(self, mock_llm_client):
        """Test reasoning from context (Deep Mode)."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Based on the context, the answer is 42."
        mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Requires 3rd arg: category_summaries
        result = await mock_llm_client.reason_from_context("Question", ["Context item"], ["Category summary"])
        
        assert "42" in result

    @pytest.mark.asyncio
    async def test_summarize_category_generates_summary(self, mock_llm_client):
        """Test category summarization."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This category contains python related facts."
        mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await mock_llm_client.summarize_category("knowledge/python", ["fact 1", "fact 2"])
        
        assert "python" in result



class TestLLMErrorHandling:
    """Tests for LLM client error handling."""

    @pytest.fixture
    def mock_llm_client(self):
        from eternal_memory.llm.client import LLMClient
        client = LLMClient(api_key="mock-key", model="gpt-4o-mini")
        client.client = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_extract_facts_handles_invalid_json(self, mock_llm_client):
        """Test graceful handling of invalid JSON from LLM."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON at all"
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        
        mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await mock_llm_client.extract_facts("test input", [])
        
        # Should return empty list, not crash
        assert result == []

    @pytest.mark.asyncio
    async def test_embedding_handles_api_error(self, mock_llm_client):
        """Test graceful handling of API errors."""
        from openai import APIError
        
        mock_llm_client.client.embeddings.create = AsyncMock(
            side_effect=APIError("API Error", request=MagicMock(), body=None)
        )
        
        with pytest.raises(APIError):
            await mock_llm_client.generate_embedding("test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
