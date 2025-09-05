"""Custom exceptions for LLM CLI."""


class LLMCLIException(Exception):
    """Base exception for LLM CLI."""
    pass


class ModelNotFoundError(LLMCLIException):
    """Raised when a model is not found."""
    pass


class ChatNotFoundError(LLMCLIException):
    """Raised when a chat is not found."""
    pass


class PromptNotFoundError(LLMCLIException):
    """Raised when a prompt file is not found."""
    pass


class ConfigurationError(LLMCLIException):
    """Raised when there's a configuration error."""
    pass


class ProviderError(LLMCLIException):
    """Raised when there's a provider-specific error."""
    pass


class AuthenticationError(LLMCLIException):
    """Raised when API authentication fails (missing or invalid API key)."""
    pass