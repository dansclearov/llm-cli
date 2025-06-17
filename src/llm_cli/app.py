from dataclasses import dataclass
from typing import Dict, Generator, List, Optional

import gradio as gr
from dotenv import load_dotenv

from llm_cli.config import setup_providers
from llm_cli.providers.base import ChatOptions
from llm_cli.utils import get_prompts, read_system_message_from_file

load_dotenv()


@dataclass
class WebConfig:
    default_model: str = "sonnet"
    default_prompt: str = "general"


class LLMClient:
    def __init__(self):
        self.registry = setup_providers()
        self.config = WebConfig()

    def stream_response(
        self,
        messages: List[Dict[str, str]],
        model_alias: str,
        options: ChatOptions = None,
    ) -> Generator[str, None, None]:
        """Stream response from the specified model."""
        if options is None:
            options = ChatOptions()

        try:
            provider, model_id = self.registry.get_provider_for_model(model_alias)

            # Stream response and yield content chunks
            for chunk in provider.stream_response(messages, model_id, options):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            # For web interface, we'll just show the error
            yield f"Error: {str(e)}"


class ChatInterface:
    def __init__(self):
        self.llm_client = LLMClient()
        self.config = WebConfig()

        # Get available models and prompts
        available_models = list(self.llm_client.registry.get_available_models().keys())
        self.model_options = available_models
        self.prompt_options = get_prompts()

    def add_user_message(
        self, user_input: str, history: Optional[List] = None
    ) -> tuple[str, List]:
        """Add user message to chat history."""
        if history is None:
            history = []
        history.append((user_input, ""))
        return "", history

    def chat(
        self, history: List, model_choice: str, prompt_choice: str
    ) -> Generator[List, None, None]:
        """Handle chat interaction and stream responses."""
        # Prepare messages
        file_name = f"prompt_{prompt_choice}.txt"
        prompt_str = read_system_message_from_file(file_name)
        messages = [{"role": "system", "content": prompt_str}]

        # Add conversation history
        if history:
            for user_msg, assistant_msg in history[:-1]:
                messages.extend(
                    [
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": assistant_msg},
                    ]
                )

        # Add current user message
        user_input = history[-1][0]
        messages.append({"role": "user", "content": user_input})

        # Set up basic options (web interface doesn't expose search/thinking controls)
        options = ChatOptions(
            enable_search=False,
            enable_thinking=True,
            show_thinking=False,  # Don't show thinking in web interface for cleaner UX
        )

        # Stream response
        response_text = ""
        for chunk in self.llm_client.stream_response(messages, model_choice, options):
            response_text += chunk
            history[-1] = (user_input, response_text)
            yield history

    def create_interface(self) -> gr.Blocks:
        """Create and configure the Gradio interface."""
        with gr.Blocks(title="LLM CLI Web Interface") as block:
            gr.Markdown("# LLM CLI Web Interface")

            with gr.Row():
                model_choice = gr.Dropdown(
                    choices=self.model_options,
                    value=self.config.default_model,
                    label="Model",
                )
                prompt_choice = gr.Dropdown(
                    choices=self.prompt_options,
                    value=self.config.default_prompt,
                    label="Initial Prompt",
                )

            chatbot = gr.Chatbot(height=400)
            state = gr.State([])

            with gr.Row():
                message = gr.Textbox(
                    placeholder="Type your message here...",
                    label="Your Message",
                    scale=4,
                )
                send_btn = gr.Button("Send", scale=1)

            # Set up message handling
            def submit_message(msg, history, model, prompt):
                # Add user message
                if msg.strip():
                    new_history = history + [(msg, "")]
                    return "", new_history, new_history
                return msg, history, history

            def bot_response(history, model, prompt):
                if history:
                    for updated_history in self.chat(history, model, prompt):
                        yield updated_history

            # Handle both Enter key and Send button
            message.submit(
                submit_message,
                [message, state, model_choice, prompt_choice],
                [message, state, chatbot],
                queue=False,
            ).then(bot_response, [state, model_choice, prompt_choice], chatbot).then(
                lambda x: x, [chatbot], [state]
            )

            send_btn.click(
                submit_message,
                [message, state, model_choice, prompt_choice],
                [message, state, chatbot],
                queue=False,
            ).then(bot_response, [state, model_choice, prompt_choice], chatbot).then(
                lambda x: x, [chatbot], [state]
            )

            # Reset button
            with gr.Row():
                reset_button = gr.Button("Reset Conversation", variant="secondary")
                reset_button.click(lambda: ([], []), outputs=[chatbot, state])

        return block


def main():
    interface = ChatInterface()
    interface.create_interface().launch(share=False, server_name="127.0.0.1")


if __name__ == "__main__":
    main()
