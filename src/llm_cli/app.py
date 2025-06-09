import gradio as gr
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Generator
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic

from llm_cli.constants import MODEL_MAPPINGS
from llm_cli.utils import read_system_message_from_file, get_prompts


load_dotenv()


@dataclass
class Config:
    models: Dict[str, str] = field(default_factory=lambda: MODEL_MAPPINGS)
    default_model: str = "sonnet"
    default_prompt: str = "general"


class LLMClient:
    def __init__(self):
        self.openai = OpenAI()
        self.anthropic = Anthropic()
        self.config = Config()

    def stream_openai_response(
        self, messages: List[Dict[str, str]], model: str
    ) -> Generator[str, None, None]:
        """Stream response from OpenAI API."""
        completion = self.openai.chat.completions.create(
            model=self.config.models.get(model, model),
            messages=messages,
            stream=True
        )
        for chunk in completion:
            message_content = chunk.choices[0].delta.content
            if message_content:
                yield message_content

    def stream_anthropic_response(
        self, messages: List[Dict[str, str]]
    ) -> Generator[str, None, None]:
        """Stream response from Anthropic API."""
        with self.anthropic.messages.stream(
            model=self.config.models["sonnet"],
            messages=messages[1:],
            system=messages[0]["content"],
            max_tokens=1024,
        ) as stream:
            for text in stream.text_stream:
                yield text


class ChatInterface:
    def __init__(self):
        self.llm_client = LLMClient()
        self.config = Config()
        self.model_options = list(self.config.models.keys())
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
                messages.extend([
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg}
                ])

        # Add current user message
        user_input = history[-1][0]
        messages.append({"role": "user", "content": user_input})

        # Get response stream based on model choice
        if model_choice in ["gpt-4o", "gpt-4-turbo"]:
            response_stream = self.llm_client.stream_openai_response(
                messages, model_choice
            )
        else:
            response_stream = self.llm_client.stream_anthropic_response(messages)

        # Stream response
        response_text = ""
        for chunk in response_stream:
            response_text += chunk
            history[-1] = (user_input, response_text)
            yield history

    def create_interface(self) -> gr.Blocks:
        """Create and configure the Gradio interface."""
        with gr.Blocks() as block:
            with gr.Row():
                model_choice = gr.Dropdown(
                    choices=self.model_options,
                    value=self.config.default_model,
                    label="Model"
                )
                prompt_choice = gr.Dropdown(
                    choices=self.prompt_options,
                    value=self.config.default_prompt,
                    label="Initial Prompt"
                )

            chatbot = gr.Chatbot()
            state = gr.State()
            message = gr.Textbox(
                placeholder="Type your message here...",
                label="Your Message"
            )

            # Set up message handling
            message.submit(
                self.add_user_message,
                [message, state],
                [message, state],
                queue=False
            ).then(
                self.chat,
                [state, model_choice, prompt_choice],
                chatbot
            )

            # Reset button
            reset_button = gr.Button("Reset")
            reset_button.click(
                lambda: ([], []),
                outputs=[chatbot, state]
            )

        return block


def main():
    interface = ChatInterface()
    interface.create_interface().launch()


if __name__ == "__main__":
    main()
