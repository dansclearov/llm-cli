import asyncio
import signal
from typing import List, Optional, Sequence

from pydantic_ai.builtin_tools import WebSearchTool
from pydantic_ai.direct import model_request_stream
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import ModelRequestParameters
from tenacity import retry, stop_after_attempt, wait_exponential

from llm_cli.llm_types import ChatOptions, ModelCapabilities
from llm_cli.registry import ModelRegistry
from llm_cli.response_handler import ResponseHandler

DEFAULT_ANTHROPIC_THINKING_BUDGET = 2048


class LLMClient:
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.interrupt_handler = None

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def chat(
        self,
        messages: Sequence[ModelMessage],
        model_alias: str,
        options: Optional[ChatOptions] = None,
    ) -> ModelResponse:
        """Get response from the specified model."""
        if options is None:
            options = ChatOptions()

        provider_name, provider_model_id = self.registry.get_provider_for_model(
            model_alias
        )

        resolved_model_id = provider_model_id
        if options.enable_search and provider_name == "openrouter":
            if not resolved_model_id.endswith(":online"):
                resolved_model_id = f"{resolved_model_id}:online"

        model_name = f"{provider_name}:{resolved_model_id}"
        capabilities = self.registry.get_model_capabilities(model_alias)

        # Validate options against capabilities
        if options.enable_search and not capabilities.supports_search:
            options.enable_search = False

        if options.enable_thinking and not capabilities.supports_thinking:
            options.enable_thinking = False

        # Start with extra_params from model config, then override with request-specific settings
        model_settings = dict(capabilities.extra_params)
        model_settings.update(options.extra_settings)

        if options.enable_thinking:
            if provider_name in {"openai", "openai-responses"}:
                model_settings.setdefault("openai_reasoning_summary", "detailed")
                model_settings.setdefault("openai_reasoning_effort", "medium")
            elif provider_name == "anthropic":
                model_settings.setdefault(
                    "anthropic_thinking",
                    {
                        "type": "enabled",
                        "budget_tokens": DEFAULT_ANTHROPIC_THINKING_BUDGET,
                    },
                )
            elif provider_name in {"google-gla", "google-vertex"}:
                model_settings.setdefault(
                    "google_thinking_config",
                    {"include_thoughts": True},
                )

        if options.enable_search:
            self._apply_search_settings(
                provider_name, provider_model_id, model_settings
            )

        model_settings_param = model_settings or None
        request_parameters = self._build_request_parameters(
            provider_name,
            provider_model_id,
            capabilities,
            options,
        )

        handler = ResponseHandler(capabilities, options)
        self.interrupt_handler = handler

        # Always operate on ModelMessage history.
        model_messages = list(messages)

        def handle_interrupt(signum, frame):
            if self.interrupt_handler:
                self.interrupt_handler.mark_interrupted()
            raise KeyboardInterrupt()

        old_handler = signal.signal(signal.SIGINT, handle_interrupt)

        try:
            handler.start_response()
            try:
                response: Optional[ModelResponse] = asyncio.run(
                    self._stream_model_response(
                        model_name,
                        model_messages,
                        model_settings_param,
                        request_parameters,
                        handler,
                    )
                )
            except KeyboardInterrupt:
                handler.finish_response()
                raise
            handler.finish_response(response)
            return response
        finally:
            signal.signal(signal.SIGINT, old_handler)
            self.interrupt_handler = None

    async def _stream_model_response(
        self,
        model_name: str,
        model_messages: List[ModelMessage],
        model_settings: Optional[dict],
        request_parameters: ModelRequestParameters,
        handler: ResponseHandler,
    ) -> ModelResponse:
        """Stream model events via the async API and return the final response."""
        async with model_request_stream(
            model=model_name,
            messages=model_messages,
            model_settings=model_settings,
            model_request_parameters=request_parameters,
        ) as stream:
            async for event in stream:
                handler.handle_event(event)
            return stream.get()

    def _apply_search_settings(
        self,
        provider_name: str,
        provider_model_id: str,
        model_settings: dict,
    ) -> None:
        """Apply provider-specific settings that enable search features."""
        if provider_name == "openrouter":
            self._enable_openrouter_web_plugin(model_settings)

    def _enable_openrouter_web_plugin(self, model_settings: dict) -> None:
        """Attach OpenRouter's `web` plugin to the request extra body."""
        extra_body = model_settings.setdefault("extra_body", {})
        plugins = extra_body.setdefault("plugins", [])
        if not any(
            isinstance(plugin, dict) and plugin.get("id") == "web" for plugin in plugins
        ):
            plugins.append({"id": "web"})

    def _build_request_parameters(
        self,
        provider_name: str,
        provider_model_id: str,
        capabilities: ModelCapabilities,
        options: ChatOptions,
    ) -> ModelRequestParameters:
        """Create provider-specific request parameters (built-in tools, etc.)."""
        builtin_tools = []

        if options.enable_search and capabilities.supports_search:
            if self._provider_supports_builtin_search(provider_name, provider_model_id):
                builtin_tools.append(WebSearchTool())
            else:
                # Provider claims to support search but no known API hook; fall back silently.
                pass

        return ModelRequestParameters(builtin_tools=builtin_tools)

    def _provider_supports_builtin_search(
        self, provider_name: str, provider_model_id: str
    ) -> bool:
        """Determine whether we can attach the built-in WebSearchTool for this provider."""
        if provider_name in {
            "anthropic",
            "openai-responses",
            "google-gla",
            "google-vertex",
        }:
            return True

        return False
