# LLM-CLI

A bare-bones command-line interface for interacting with large language models (LLMs) like GPT-4o and Claude 3.5 Sonnet.

## Features

- Interact with OpenAI's GPT-4o and Anthropic's Claude models
- Command-line interface for easy access
- Optional Gradio web interface
- Customizable system prompts
- Support for multi-line input

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

## Usage

### Command-line Interface

Run the CLI with:

```
llm-cli [prompt] [-m MODEL]
```

- `prompt`: Optional. Specify the initial prompt for the chat session (default: "general")
- `-m` or `--model`: Optional. Specify which model to use: "gpt-4o", "gpt-4-turbo", or "sonnet" (default: "gpt-4o")

Example:
```
llm-cli concise -m sonnet
```

Input '>' by itself to enter multi-line mode. End multi-line input with a line containing only ">>".

### Gradio Web Interface

To launch the Gradio web interface:

```
llm-cli-app
```

### Prompts

The `llm_cli/prompts` folder contains prompt files in the format `prompt_###.txt`, where `###` is any name you choose. You can specify these prompts when running the app by using the corresponding name.

For example:
- `prompt_general.txt` can be used with `llm-cli general`
- `prompt_concise.txt` can be used with `llm-cli concise`

To add a new prompt, simply create a new file in the `prompts` folder following the naming convention.

## Contributing

This project is primarily for personal use, but feel free to fork and modify it for your own needs.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
