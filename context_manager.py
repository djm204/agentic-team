"""
Context window management utilities.
"""
from typing import List, Dict, Any
import tiktoken


class ContextManager:
    """Manages context windows to prevent over-saturation."""
    
    def __init__(self, model: str = "gpt-4", max_tokens: int = None):
        """
        Initialize context manager.
        
        Args:
            model: Model name for token counting
            max_tokens: Maximum tokens allowed (defaults based on model)
        """
        self.model = model
        self.encoding = None
        
        try:
            # Try to get encoding for the model
            if "gpt-4" in model.lower() or "gpt-3.5" in model.lower():
                self.encoding = tiktoken.encoding_for_model(model)
            else:
                # Default to cl100k_base (used by GPT-4)
                self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback encoding
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Set max tokens based on model
        if max_tokens is None:
            if "gpt-4" in model.lower():
                # GPT-4 has 128k context, but we'll be conservative
                self.max_tokens = 100000
            elif "gpt-3.5" in model.lower():
                self.max_tokens = 16000
            else:
                self.max_tokens = 32000
        else:
            self.max_tokens = max_tokens
        
        # Reserve tokens for response
        self.reserved_tokens = 4000
        self.max_input_tokens = self.max_tokens - self.reserved_tokens
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not self.encoding:
            # Fallback: rough estimate (4 chars per token)
            return len(text) // 4
        
        return len(self.encoding.encode(text))
    
    def truncate_to_fit(
        self,
        text: str,
        max_tokens: int = None,
        strategy: str = "end"
    ) -> str:
        """
        Truncate text to fit within token limit.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum tokens (defaults to max_input_tokens)
            strategy: Truncation strategy ('end', 'start', 'middle')
        
        Returns:
            Truncated text
        """
        if max_tokens is None:
            max_tokens = self.max_input_tokens
        
        current_tokens = self.count_tokens(text)
        
        if current_tokens <= max_tokens:
            return text
        
        # Truncate based on strategy
        if strategy == "end":
            # Truncate from end
            tokens_to_remove = current_tokens - max_tokens
            encoded = self.encoding.encode(text)
            truncated = encoded[:-tokens_to_remove]
            return self.encoding.decode(truncated)
        
        elif strategy == "start":
            # Truncate from start
            tokens_to_remove = current_tokens - max_tokens
            encoded = self.encoding.encode(text)
            truncated = encoded[tokens_to_remove:]
            return self.encoding.decode(truncated)
        
        elif strategy == "middle":
            # Truncate from middle
            tokens_to_remove = current_tokens - max_tokens
            remove_from_start = tokens_to_remove // 2
            remove_from_end = tokens_to_remove - remove_from_start
            
            encoded = self.encoding.encode(text)
            truncated = encoded[remove_from_start:-remove_from_end] if remove_from_end > 0 else encoded[remove_from_start:]
            return self.encoding.decode(truncated)
        
        return text
    
    def summarize_for_context(
        self,
        text: str,
        max_tokens: int = None,
        preserve_structure: bool = True
    ) -> str:
        """
        Create a summary of text to fit in context.
        
        Args:
            text: Text to summarize
            max_tokens: Maximum tokens for summary
            preserve_structure: Whether to preserve code structure
        
        Returns:
            Summarized text
        """
        if max_tokens is None:
            max_tokens = self.max_input_tokens // 4  # Summary should be ~25% of original
        
        current_tokens = self.count_tokens(text)
        
        if current_tokens <= max_tokens:
            return text
        
        # If it's code, try to preserve structure
        if preserve_structure and self._looks_like_code(text):
            return self._summarize_code(text, max_tokens)
        
        # Otherwise, truncate intelligently
        return self.truncate_to_fit(text, max_tokens, strategy="middle")
    
    def _looks_like_code(self, text: str) -> bool:
        """Check if text looks like code."""
        code_indicators = ['def ', 'class ', 'import ', 'function ', '{', '}', '()', '=>']
        return any(indicator in text[:500] for indicator in code_indicators)
    
    def _summarize_code(self, text: str, max_tokens: int) -> str:
        """Summarize code while preserving structure."""
        lines = text.split('\n')
        important_lines = []
        
        # Keep imports, class/function definitions, and key logic
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith(('import ', 'from ', 'def ', 'class ', '#', '"""', "'''")) or
                any(keyword in stripped for keyword in ['return', 'raise', 'assert', 'if __name__'])):
                important_lines.append(line)
        
        summarized = '\n'.join(important_lines)
        
        # If still too long, truncate
        if self.count_tokens(summarized) > max_tokens:
            return self.truncate_to_fit(summarized, max_tokens, strategy="end")
        
        return summarized
    
    def check_context_usage(
        self,
        *texts: str,
        warn_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Check context window usage for multiple texts.
        
        Args:
            *texts: Texts to check
            warn_threshold: Threshold for warning (0.0-1.0)
        
        Returns:
            Dictionary with usage statistics
        """
        total_tokens = sum(self.count_tokens(text) for text in texts)
        usage_percent = (total_tokens / self.max_input_tokens) * 100
        
        result = {
            "total_tokens": total_tokens,
            "max_tokens": self.max_input_tokens,
            "usage_percent": usage_percent,
            "within_limit": total_tokens <= self.max_input_tokens,
            "warning": usage_percent >= (warn_threshold * 100)
        }
        
        if result["warning"]:
            print(f"⚠️ Context window usage: {usage_percent:.1f}% ({total_tokens}/{self.max_input_tokens} tokens)")
        
        if not result["within_limit"]:
            print(f"❌ Context window exceeded! {total_tokens}/{self.max_input_tokens} tokens")
        
        return result
