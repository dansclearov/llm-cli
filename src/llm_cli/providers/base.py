from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional


@dataclass
class ModelCapabilities:
    """Capabilities of a specific model."""

    supports_search: bool = False
    supports_thinking: bool = False
    max_tokens: Optional[int] = None  # Only set for providers that require it


@dataclass
class StreamChunk:
    """A chunk of streamed response data."""

    content: Optional[str] = None
    thinking: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatOptions:
    """Options for chat requests."""

    enable_search: bool = False
    enable_thinking: bool = True
    show_thinking: bool = True


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get capabilities for a specific model."""
        pass

    @abstractmethod
    def stream_response(
        self, messages: List[Dict[str, str]], model: str, options: ChatOptions
    ) -> Generator[StreamChunk, None, None]:
        """Stream response from the model."""
        pass

    @abstractmethod
    def get_available_models(self) -> Dict[str, str]:
        """Get mapping of model aliases to actual model IDs."""
        pass
