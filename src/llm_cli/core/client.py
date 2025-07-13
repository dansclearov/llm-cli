import signal
from typing import Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from llm_cli.config.settings import setup_providers
from llm_cli.providers.base import ChatOptions
from llm_cli.response_handler import ResponseHandler


class LLMClient:
    def __init__(self):
        self.registry = setup_providers()
        self.interrupt_handler = None

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def chat(
        self,
        messages: List[Dict[str, str]],
        model_alias: str,
        options: ChatOptions = None,
    ) -> str:
        """Get response from the specified model."""
        if options is None:
            options = ChatOptions()

        try:
            provider, model_id = self.registry.get_provider_for_model(model_alias)
            capabilities = provider.get_capabilities(model_id)

            # Validate options against capabilities
            if options.enable_search and not capabilities.supports_search:
                print(f"Warning: {model_alias} doesn't support search.")
                options.enable_search = False

            # Set up response handler
            handler = ResponseHandler(capabilities, options)
            self.interrupt_handler = handler

            # Set up signal handler for interrupt during streaming
            def handle_interrupt(signum, frame):
                if self.interrupt_handler:
                    self.interrupt_handler.mark_interrupted()
                    raise KeyboardInterrupt()

            old_handler = signal.signal(signal.SIGINT, handle_interrupt)

            try:
                # Stream response
                handler.start_response()
                for chunk in provider.stream_response(messages, model_id, options):
                    handler.handle_chunk(chunk)
                handler.finish_response()
            except KeyboardInterrupt:
                # Handle interrupt gracefully during streaming
                handler.finish_response()
            finally:
                # Restore original signal handler
                signal.signal(signal.SIGINT, old_handler)
                self.interrupt_handler = None

            return handler.get_full_response()

        except Exception as e:
            # Re-raise to let tenacity handle retries
            raise e