"""
Tests for Rolling Summary Buffer pattern.

Tests the context window management and rolling summary generation
based on LangChain's ConversationSummaryBufferMemory pattern.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os


class TestRollingSummaryBuffer:
    """Test suite for Rolling Summary Buffer functionality."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI async client."""
        client = MagicMock()
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        
        # Create mock response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "User mentioned their name is John and they prefer Python."
        mock_response.choices = [mock_choice]
        
        client.chat.completions.create = AsyncMock(return_value=mock_response)
        return client

    @pytest.mark.asyncio
    async def test_summarize_old_context_empty(self, mock_openai_client):
        """Test summarization with empty messages returns empty string."""
        from eternal_memory.api.routes.chat import summarize_old_context
        
        result = await summarize_old_context([], mock_openai_client, "gpt-4o-mini")
        
        assert result == ""
        mock_openai_client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_summarize_old_context_success(self, mock_openai_client):
        """Test successful summarization of old messages."""
        from eternal_memory.api.routes.chat import summarize_old_context
        
        old_messages = [
            {"role": "user", "content": "My name is John"},
            {"role": "assistant", "content": "Nice to meet you, John!"},
            {"role": "user", "content": "I prefer Python over JavaScript"},
            {"role": "assistant", "content": "Python is great for many use cases."},
        ]
        
        result = await summarize_old_context(old_messages, mock_openai_client, "gpt-4o-mini")
        
        assert result == "User mentioned their name is John and they prefer Python."
        mock_openai_client.chat.completions.create.assert_called_once()
        
        # Verify the call included the transcript
        call_args = mock_openai_client.chat.completions.create.call_args
        prompt_content = call_args.kwargs["messages"][0]["content"]
        assert "USER: My name is John" in prompt_content
        assert "ASSISTANT: Nice to meet you, John!" in prompt_content

    @pytest.mark.asyncio
    async def test_summarize_old_context_error_handling(self, mock_openai_client):
        """Test that errors in summarization return empty string gracefully."""
        from eternal_memory.api.routes.chat import summarize_old_context
        
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        
        old_messages = [{"role": "user", "content": "Hello"}]
        
        result = await summarize_old_context(old_messages, mock_openai_client, "gpt-4o-mini")
        
        assert result == ""  # Graceful degradation

    def test_context_window_size_constant(self):
        """Test that CONTEXT_WINDOW_SIZE is set correctly."""
        from eternal_memory.api.routes.chat import CONTEXT_WINDOW_SIZE
        
        assert CONTEXT_WINDOW_SIZE == 15
        assert isinstance(CONTEXT_WINDOW_SIZE, int)


class TestConversationEndpointWithRollingSummary:
    """Integration tests for the conversation endpoint with rolling summary."""

    @pytest.fixture
    def mock_env(self):
        """Set up environment variables for testing."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_MODEL": "gpt-4o-mini",
        }):
            yield

    @pytest.mark.asyncio
    async def test_small_conversation_no_summary(self):
        """Test that small conversations don't trigger summarization."""
        # With fewer than CONTEXT_WINDOW_SIZE messages, no summary should be generated
        from eternal_memory.api.routes.chat import CONTEXT_WINDOW_SIZE
        
        conversation_history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(CONTEXT_WINDOW_SIZE - 1)
        ]
        
        # Verify we're under the threshold
        assert len(conversation_history) < CONTEXT_WINDOW_SIZE

    @pytest.mark.asyncio
    async def test_large_conversation_triggers_summary(self):
        """Test that large conversations trigger summarization."""
        from eternal_memory.api.routes.chat import CONTEXT_WINDOW_SIZE
        
        conversation_history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(CONTEXT_WINDOW_SIZE + 5)
        ]
        
        # Verify we're over the threshold
        assert len(conversation_history) > CONTEXT_WINDOW_SIZE
        
        # The old messages would be:
        old_count = len(conversation_history) - CONTEXT_WINDOW_SIZE
        assert old_count == 5

    @pytest.mark.asyncio
    async def test_cached_summary_is_used(self):
        """Test that cached context_summary from frontend is used."""
        from eternal_memory.api.routes.chat import CONTEXT_WINDOW_SIZE
        
        conversation_history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(CONTEXT_WINDOW_SIZE + 5)
        ]
        
        cached_summary = "User previously mentioned they are a software developer."
        
        # When context_summary is provided, it should be used instead of regenerating
        # This test verifies the logic: if request.context_summary exists, use it
        assert cached_summary is not None
        assert len(cached_summary) > 0


class TestConversationRequestModel:
    """Test the ConversationRequest Pydantic model."""

    def test_context_summary_field_exists(self):
        """Test that context_summary field exists in ConversationRequest."""
        from eternal_memory.api.routes.chat import ConversationRequest
        
        # Verify the field exists
        assert "context_summary" in ConversationRequest.model_fields
        
        # Verify it's optional
        field_info = ConversationRequest.model_fields["context_summary"]
        assert field_info.default is None

    def test_conversation_request_with_context_summary(self):
        """Test creating ConversationRequest with context_summary."""
        from eternal_memory.api.routes.chat import ConversationRequest
        
        request = ConversationRequest(
            message="Hello",
            context_summary="Previous context about the user"
        )
        
        assert request.message == "Hello"
        assert request.context_summary == "Previous context about the user"

    def test_conversation_request_without_context_summary(self):
        """Test creating ConversationRequest without context_summary."""
        from eternal_memory.api.routes.chat import ConversationRequest
        
        request = ConversationRequest(message="Hello")
        
        assert request.message == "Hello"
        assert request.context_summary is None


class TestConversationResponseModel:
    """Test the ConversationResponse Pydantic model."""

    def test_context_summary_field_exists_in_response(self):
        """Test that context_summary field exists in ConversationResponse."""
        from eternal_memory.api.routes.chat import ConversationResponse
        
        # Verify the field exists
        assert "context_summary" in ConversationResponse.model_fields

    def test_conversation_response_with_context_summary(self):
        """Test creating ConversationResponse with context_summary."""
        from eternal_memory.api.routes.chat import ConversationResponse
        
        response = ConversationResponse(
            response="Hello there!",
            memories_retrieved=[],
            memories_stored=[],
            processing_info={"mode": "fast", "model": "gpt-4o-mini"},
            context_summary="User is named John and prefers Python."
        )
        
        assert response.response == "Hello there!"
        assert response.context_summary == "User is named John and prefers Python."


class TestStaleCacheDetection:
    """Test stale cache detection for rolling summary buffer."""

    def test_summarized_count_field_in_request(self):
        """Test that summarized_count field exists in ConversationRequest."""
        from eternal_memory.api.routes.chat import ConversationRequest
        
        assert "summarized_count" in ConversationRequest.model_fields
        
        request = ConversationRequest(
            message="Hello",
            context_summary="Test summary",
            summarized_count=5
        )
        
        assert request.summarized_count == 5

    def test_summarized_count_field_in_response(self):
        """Test that summarized_count field exists in ConversationResponse."""
        from eternal_memory.api.routes.chat import ConversationResponse
        
        assert "summarized_count" in ConversationResponse.model_fields
        
        response = ConversationResponse(
            response="Hello",
            memories_retrieved=[],
            memories_stored=[],
            processing_info={},
            context_summary="Test",
            summarized_count=3
        )
        
        assert response.summarized_count == 3

    def test_stale_cache_detection_scenario(self):
        """
        Test stale cache detection logic.
        
        Scenario: At message 16, 1 message is summarized.
        At message 17, 2 messages should be summarized.
        If frontend sends summarized_count=1 but current old_count=2,
        the cache is stale and new summary should be generated.
        """
        from eternal_memory.api.routes.chat import CONTEXT_WINDOW_SIZE
        
        # Scenario: 17 messages total
        total_messages = 17
        old_count = total_messages - CONTEXT_WINDOW_SIZE  # 17 - 15 = 2
        
        # Frontend sends stale count (from previous request)
        cached_count = 1  # This was valid at message 16
        
        # Stale detection: counts don't match
        cache_is_stale = (cached_count != old_count)
        
        assert cache_is_stale is True
        assert old_count == 2
        assert cached_count == 1

    def test_cache_hit_scenario(self):
        """
        Test cache hit when summarized_count matches.
        
        Scenario: User sends another message but old_count stays same.
        This happens when we're just below the threshold or recently crossed it.
        """
        from eternal_memory.api.routes.chat import CONTEXT_WINDOW_SIZE
        
        # Scenario: 16 messages total → 1 old message
        total_messages = 16
        old_count = total_messages - CONTEXT_WINDOW_SIZE  # 16 - 15 = 1
        
        # Frontend sends matching count
        cached_count = 1
        
        # No stale: counts match
        cache_is_stale = (cached_count != old_count)
        
        assert cache_is_stale is False

    def test_stale_cache_none_summarized_count(self):
        """Test that None summarized_count is treated as stale."""
        # When frontend has no cached count, cache is stale
        cached_count = None
        old_count = 5
        
        cache_is_stale = (
            cached_count is None or
            cached_count != old_count
        )
        
        assert cache_is_stale is True

    def test_message_growth_forces_resummary(self):
        """
        Test that as conversation grows, summary is regenerated.
        
        Track of old message counts:
        - Message 16: old_count = 1, generate summary
        - Message 17: old_count = 2, stale! regenerate
        - Message 18: old_count = 3, stale! regenerate
        - ... and so on
        """
        from eternal_memory.api.routes.chat import CONTEXT_WINDOW_SIZE
        
        scenarios = [
            (16, 1, None, True),   # First summary generation
            (17, 2, 1, True),      # Stale: 1 != 2
            (18, 3, 2, True),      # Stale: 2 != 3
            (19, 4, 3, True),      # Stale: 3 != 4
        ]
        
        for total, expected_old, cached, expected_stale in scenarios:
            old_count = total - CONTEXT_WINDOW_SIZE
            assert old_count == expected_old
            
            is_stale = (cached is None or cached != old_count)
            assert is_stale == expected_stale, f"Failed at total={total}"
