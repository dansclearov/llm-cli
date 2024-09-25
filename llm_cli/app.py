import gradio as gr

from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic

from llm_cli.utils import read_system_message_from_file, get_prompts

load_dotenv()

openai = OpenAI()
anthropic = Anthropic()


def stream_openai_response(messages, model="gpt-4o"):
    completion = openai.chat.completions.create(
        model=model, messages=messages, stream=True
    )

    for chunk in completion:
        message_content = chunk.choices[0].delta.content
        if message_content:
            yield message_content


def stream_anthropic_response(messages):
    with anthropic.messages.stream(
        model="claude-3-5-sonnet-20240620",
        messages=messages[1:],
        system=messages[0]["content"],
        max_tokens=1024,
    ) as stream:
        for text in stream.text_stream:
            yield text


def add_user_message(user_input, history):
    if history is None:
        history = []
    history.append((user_input, ""))
    return "", history


def chat(history, model_choice, prompt_choice):
    file_name = f"prompt_{prompt_choice}.txt"
    prompt_str = read_system_message_from_file(file_name)
    messages = [{"role": "system", "content": prompt_str}]

    if history:
        for user_msg, assistant_msg in history[:-1]:
            messages.extend([
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg}
            ])

    user_input = history[-1][0]
    messages.append({"role": "user", "content": user_input})

    if model_choice in ["gpt-4o", "gpt-4-turbo"]:
        response_stream = stream_openai_response(messages, model=model_choice)
    else:
        response_stream = stream_anthropic_response(messages)

    response_text = ""
    for chunk in response_stream:
        response_text += chunk
        history[-1] = (user_input, response_text)
        yield history


model_options = ["gpt-4o", "gpt-4-turbo", "claude-3-5-sonnet-20240620"]
prompt_options = get_prompts()

with gr.Blocks() as block:
    with gr.Row():
        model_choice = gr.Dropdown(choices=model_options,
                                   value="claude-3-5-sonnet-20240620",
                                   label="Model")
        prompt_choice = gr.Dropdown(choices=prompt_options,
                                    value="general",
                                    label="Initial Prompt")

    chatbot = gr.Chatbot()
    state = gr.State()
    message = gr.Textbox(placeholder="Type your message here...",
                         label="Your Message")

    message.submit(add_user_message, [message, state], [message, state],
                   queue=False).then(
        chat, [state, model_choice, prompt_choice], chatbot
    )

    reset_button = gr.Button("Reset")
    reset_button.click(lambda: ([], []), outputs=[chatbot, state])


def main():
    block.launch()


if __name__ == "__main__":
    main()
