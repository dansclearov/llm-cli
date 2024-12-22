# LLM-CLI

A bare-bones command-line interface for interacting with large language models (LLMs) like GPT-4o and Claude 3.5 Sonnet.

## Features

- Interact with OpenAI's GPT-4o and Anthropic's Claude models
- Command-line interface for easy access
- Optional Gradio web interface
- Customizable system prompts with user-specific overrides
- Support for multi-line input
- Chat history management with save/load functionality
- Automatic session persistence
- Retry logic for API failures
- Chat history pagination

## Installation

### Using Poetry (for development)

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/llm-cli-ui.git
   cd llm-cli-ui
   ```

2. Install dependencies using Poetry:
   ```
   poetry install
   ```

### Global Installation with pipx

For global installation, you have two options:

1. Install directly from the GitHub repository:
   ```
   pipx install git+https://github.com/dansclearov/llm-cli.git
   ```

2. Install from a local copy (useful if you've cloned the project and made modifications):
   ```
   # Navigate to the project directory
   cd path/to/llm-cli
   
   # Install the local package
   pipx install -e .
   ```

   If you make changes to your local copy and want to update the installed version:
   ```
   pipx install --force -e .
   ```

I recommend `pipx` for managing global CLI packages, allowing you to use the `llm-cli` command from anywhere in your system, as well as adding aliases for models you use frequently in your shell configuration.

### Environment Setup

Set up your environment variables:
Create a `.env` file in the root directory and add your API keys:
```
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

Optionally, you can customize the chat history directory and temporary file name:
```
LLM_CLI_CHAT_DIR=/path/to/chat/history
LLM_CLI_TEMP_FILE=custom_temp_session.json  # Default: temp_session.json
```

By default, chat histories are stored in:
- Linux: `~/.local/share/llm_cli/chats/`
- macOS: `~/Library/Application Support/llm_cli/chats/`
- Windows: `C:\Users\<username>\AppData\Local\llm_cli\chats\`

## Usage

### Command-line Interface

Run the CLI with:

```
llm-cli [prompt] [-m MODEL] [-l HISTORY_FILE]
```

- `prompt`: Optional. Specify the initial prompt for the chat session (default: "general")
- `-m` or `--model`: Optional. Specify which model to use: "gpt-4o", "gpt-4-turbo", or "sonnet" (default: "gpt-4o")
- `-l` or `--load`: Optional. Load a previous chat history file at startup

Input '>' by itself to enter multi-line mode. End multi-line input with a line containing only ">>".

### Special Commands

During a chat session, you can use the following commands:

- `%save filename`: Save the current chat history to a file
- `%load filename`: Load a chat history from a file
- `%append filename`: Append messages from another chat history file

### Chat History Management

Your chat session is automatically saved to a temporary file when exiting (either normally or due to an interruption). This temporary file gets overwritten with each new session, serving as a safety net in case of accidental closure. For persistent storage, use the `%save` command to save your chat history with a custom filename.

### Gradio Web Interface

To launch the Gradio web interface:

```
llm-cli-app
```

### Prompts

The system looks for prompt files in two locations:
1. User config directory:
   - Linux: `~/.config/llm_cli/prompts/`
   - macOS: `~/Library/Application Support/llm_cli/prompts/`
   - Windows: `C:\Users\<username>\AppData\Local\llm_cli\prompts\`
2. Package's built-in prompts directory

Prompt files should follow the format `prompt_###.txt`, where `###` is any name you choose. You can specify these prompts when running the app by using the corresponding name.

For example:
- `prompt_general.txt` can be used with `llm-cli general`
- `prompt_concise.txt` can be used with `llm-cli concise`

To add a custom prompt, create a new file in your user config prompts directory following the naming convention. User prompts take precedence over package prompts with the same name.

## Testing

Run the test suite with pytest:
```bash
pytest
```

## Contributing

This project is primarily for personal use, but feel free to fork and modify it for your own needs.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
