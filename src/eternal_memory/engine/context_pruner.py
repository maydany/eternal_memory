"""
Context Pruner

Utilities for managing LLM context window by trimming large content blocks.
"""

from typing import List, Dict, Any

class ContextPruner:
    """
    Manages context window by trimming messages.
    """
    
    def __init__(self, max_tokens: int = 12000, chars_per_token: int = 4):
        self.max_tokens = max_tokens
        self.chars_per_token = chars_per_token
        
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a string."""
        if not text:
            return 0
        return len(text) // self.chars_per_token
        
    def trim_text(self, text: str, head_chars: int = 1000, tail_chars: int = 1000) -> str:
        """
        Soft trim text: keep head and tail, remove middle.
        Returns original text if it's shorter than head + tail.
        """
        if not text or len(text) <= (head_chars + tail_chars):
            return text
            
        head = text[:head_chars]
        tail = text[-tail_chars:]
        removed_count = len(text) - (head_chars + tail_chars)
        
        return f"{head}\n\n[...SNIP: {removed_count} chars removed for brevity...]\n\n{tail}"
        
    def prune_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prune a list of messages to fit within max_tokens.
        
        Strategy:
        1. Calculate total estimated tokens.
        2. If within limit, return as is.
        3. If exceeded, iterate through messages (oldest first, preserving System and last 2 User/Assistant).
        4. Trim long messages (> 500 tokens).
        5. If still exceeded, could remove messages (not implemented yet, safe trim first).
        """
        if not messages:
            return messages
            
        total_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in messages)
        
        if total_tokens <= self.max_tokens:
            return messages
            
        print(f"⚠️ Context limit exceeded ({total_tokens} > {self.max_tokens}). Pruning...")
        
        pruned_messages = []
        # Preserve indices we don't want to touch easily
        # 1. System prompt (usually index 0)
        # 2. Last 2 messages (immediate context)
        protected_indices = {0, len(messages)-1, len(messages)-2}
        
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            tokens = self.estimate_tokens(content)
            
            # If it's a long message and NOT protected (or even if protected but HUGE?), trim it.
            # We'll be conservative: if it's > 500 tokens (approx 2000 chars) and not the very last message.
            if tokens > 500 and i != len(messages) - 1:
                # Determine trim aggressiveness based on how far back it is
                # Older messages get trimmed more aggressively
                if i in protected_indices:
                    # Mild trim for protected
                    new_content = self.trim_text(content, head_chars=2000, tail_chars=2000)
                else:
                    # Aggressive trim for middle history
                    new_content = self.trim_text(content, head_chars=500, tail_chars=500)
                
                msg_copy = msg.copy()
                msg_copy["content"] = new_content
                pruned_messages.append(msg_copy)
            else:
                pruned_messages.append(msg)
                
        new_total = sum(self.estimate_tokens(m.get("content", "")) for m in pruned_messages)
        print(f"✅ Pruned context from {total_tokens} to {new_total} tokens.")
        
        return pruned_messages
