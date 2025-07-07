# LLM-CLI

A multi-provider command-line interface for interacting with large language models (LLMs) like GPT-4o, Claude 4, DeepSeek, Gemini, and Grok.

## Features

- **Multi-provider support**: OpenAI, Anthropic, DeepSeek, xAI (Grok), Google Gemini
- **Centralized model management**: All models and aliases configured in YAML
- **Interactive chat management**: Browse, resume, and continue previous conversations
- **Real-time streaming**: Live response display with thinking traces (DeepSeek)
- **Customizable prompts**: User-specific prompt overrides
- **Session persistence**: Automatic chat saving with smart titles
- **Model capabilities**: Per-model search and thinking mode support
- **Flexible configuration**: User-configurable defaults and model aliases

## Supported Models

- **OpenAI**: GPT-4o, GPT-4.5, GPT-4 Turbo, o4-mini, o3
- **Anthropic**: Claude Sonnet 4, Claude Opus 4  
- **DeepSeek**: DeepSeek Reasoner (with reasoning traces)
- **xAI**: Grok 3 (with search capabilities)
- **Google**: Gemini 2.5 Pro, Gemini 2.5 Flash

## Installation

### Using uv (recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/dansclearov/llm-cli.git
   cd llm-cli
   ```

2. Install dependencies:
   ```bash
   uv install
   ```

### Global Installation with pipx

Install directly from GitHub:
```bash
pipx install git+https://github.com/dansclearov/llm-cli.git
```

Or install from local copy:
```bash
cd llm-cli
pipx install -e .
# Update after changes:
pipx install --force -e .
```

## Configuration

### API Keys

Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
XAI_API_KEY=your_xai_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### Model Configuration

Models and aliases are configured in `src/llm_cli/models.yaml`:

```yaml
aliases:
  # Default model (used when no -m provided)
  default: anthropic/claude-sonnet-4-20250514
  
  # Custom aliases
  sonnet: anthropic/claude-sonnet-4-20250514
  opus: anthropic/claude-opus-4-20250514
  gpt-4o: openai/chatgpt-4o-latest
  gpt-4.5: openai/gpt-4.5-preview
  r1: deepseek/deepseek-reasoner

# Model capabilities and settings
anthropic:
  claude-sonnet-4-20250514:
    supports_search: false
    supports_thinking: false
    max_tokens: 8192
  # ... more models
```

You can override this with a user config file at `~/.config/llm_cli/models.yaml`.

### Chat Storage

Chat histories are stored in:
- **Linux**: `~/.local/share/llm_cli/chats/`
- **macOS**: `~/Library/Application Support/llm_cli/chats/`
- **Windows**: `C:\Users\<username>\AppData\Local\llm_cli\chats\`

Override with `LLM_CLI_CHAT_DIR` environment variable.

## Usage

### Basic Usage

```bash
# Use default model and prompt
llm-cli

# Specify model and prompt
llm-cli concise -m sonnet

# Use model alias
llm-cli -m gpt-4o

# Enable search (if supported)
llm-cli --search -m grok-3

# Enable thinking mode with reasoning traces
llm-cli --thinking -m r1
```

### Chat Management

```bash
# Resume last chat
llm-cli -c

# Show chat selector
llm-cli -r

# Resume specific chat by ID
llm-cli -r chat_20240622_143022_a1b2c3d4
```

### Available Options

```
llm-cli [prompt] [options]

Arguments:
  prompt              System prompt name (default: general)

Options:
  -m, --model         Model to use (default from config)
  -r, --resume        Resume chat (with ID or show selector)
  -c, --continue      Continue most recent chat
  --search            Enable search (if supported)
  --thinking          Enable thinking mode (default: true)
  --hide-thinking     Hide thinking trace display
```

### Input Methods

- **Single line**: Type normally and press Enter
- **Multi-line**: Type `>` and press Enter, then type multiple lines, end with `>>`

### Interactive Features

- **Auto-save**: Chats save automatically after each exchange
- **Smart titles**: Automatically generated based on conversation content
- **Streaming output**: Real-time response display as models generate
- **Thinking traces**: Styled reasoning process display for supported models
- **Interrupt handling**: Ctrl+C gracefully stops generation

## Prompts

Prompts are loaded from:
1. **User config**: `~/.config/llm_cli/prompts/` (takes precedence)
2. **Built-in**: Package prompts directory

Create custom prompts as `prompt_[name].txt`:
- `prompt_general.txt` → `llm-cli general`
- `prompt_concise.txt` → `llm-cli concise`
- `prompt_coding.txt` → `llm-cli coding`

## Development

### Setup
```bash
uv install --group dev
```

### Code Quality
```bash
# Format code
black .
isort .

# Type checking
mypy .

# Run tests
pytest
```

### Architecture

- **Provider system**: Unified interface for all LLM APIs
- **Model registry**: YAML-based configuration and discovery
- **Chat management**: Rich interactive session handling
- **Streaming**: Real-time response display with provider-specific features
- **Configuration**: Dual-location config system (user + package)

## License

MIT License - see LICENSE file for details.