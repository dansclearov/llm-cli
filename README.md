# LLM-CLI

A multi-provider command-line interface for interacting with large language models. Features rich terminal UI, comprehensive chat management, and unified streaming responses across providers.

![Demo](demo.gif)

## ✨ Features

- **Multi-provider support**: OpenAI, Anthropic, DeepSeek, xAI, Gemini, OpenRouter
- **Advanced reasoning models**: Supports OpenAI o-series, DeepSeek R1  
- **Rich terminal UI**: Styled output, interactive chat selection, vim mode support
- **Intelligent chat management**: Auto-save, smart titles, resume/continue conversations
- **Real-time streaming**: Live responses with provider-specific capabilities
- **Centralized configuration**: YAML-based model management with user overrides
- **Flexible prompts**: User-customizable system prompts with dual-location loading

## 🚀 Quick Start

```bash
# Install from GitHub
uv tool install git+https://github.com/dansclearov/llm-cli.git

# Set up API keys (add to ~/.zshrc or ~/.bashrc)
export OPENAI_API_KEY=your_openai_api_key
export ANTHROPIC_API_KEY=your_anthropic_api_key

# Start chatting
llm-cli
llm-cli concise -m sonnet
```

**Or for local development:**

```bash
# Clone and install locally
git clone https://github.com/dansclearov/llm-cli.git
cd llm-cli
cp .env.example .env  # Edit with your API keys
uv tool install -e .
```

## 🔧 Configuration

### API Keys

Set up your API keys in environment variables or `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key  
DEEPSEEK_API_KEY=your_deepseek_api_key
XAI_API_KEY=your_xai_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

### Model Configuration

Models are centrally configured in `src/llm_cli/models.yaml` with user overrides at `~/.config/llm_cli/models.yaml`:

```yaml
aliases:
  default: gpt-4o
  sonnet: anthropic/claude-sonnet-4-20250514
  opus: anthropic/claude-opus-4-1-20250805
  gpt-4o: openai/chatgpt-4o-latest
  r1: deepseek/deepseek-reasoner
  r1-free: "openrouter/deepseek/deepseek-r1-0528:free"
  kimi: openrouter/moonshotai/kimi-k2
  grok-4: openrouter/x-ai/grok-4

anthropic:
  claude-sonnet-4-20250514:
    supports_search: false
    supports_thinking: false
    max_tokens: 8192

openai:
  gpt-5:
    supports_thinking: true

openrouter:
  "deepseek/deepseek-r1-0528:free":
    supports_thinking: true
    extra_params:
      provider:
        quantizations: ["fp8", "fp16", "bf16", "fp32"]
```

### Configuration Locations

View all configuration paths:
```bash
llm-cli --user-paths
```

**Standard paths:**
- **Linux**: `~/.config/llm_cli/` (config), `~/.local/share/llm_cli/chats/` (data)
- **macOS**: `~/Library/Application Support/llm_cli/`
- **Windows**: `C:\Users\<username>\AppData\Local\llm_cli\`

**Environment overrides:**
- `LLM_CLI_CHAT_DIR`: Custom chat storage directory

## 💬 Usage

### Basic Commands

```bash
# Start new chat with defaults
llm-cli

# Use specific prompt and model
llm-cli concise -m sonnet

# Enable model-specific features
llm-cli --search -m grok-4           # Search capability
llm-cli --no-thinking -m r1          # Disable thinking mode
llm-cli --hide-thinking -m r1        # Hide thinking display
```

### Chat Management

```bash
# Continue last chat
llm-cli -c

# Interactive chat selector
llm-cli -r

# Resume specific chat
llm-cli -r chat_20240622_143022_a1b2c3d4
```

### Complete Options

```
Usage: llm-cli [prompt] [options]

Arguments:
  prompt               System prompt name (default: general)

Options:
  -m, --model          Model to use (default from config)
  -r, --resume [ID]    Resume chat (with ID or show selector)  
  -c, --continue       Continue most recent chat
  --search             Enable search (if supported)
  --no-thinking        Disable thinking mode completely
  --hide-thinking      Hide thinking trace display
  --user-paths         Show all configuration paths and exit
  -h, --help           Show this help message
```

### Input Methods

- **Single line**: Type and press Enter
- **Multi-line**: Use `Shift+Enter` for newlines, Enter to submit
- **Vim mode**: Type `/vim` in chat to toggle vim keybindings
- **Interrupt**: `Ctrl+C` gracefully stops generation

### Interactive Features

#### Chat Selector Navigation
```
↑/↓, k/j, Ctrl+P/N    Navigate conversations
Enter                 Select conversation
n/p, Ctrl+L/H         Next/previous page
dd                    Delete conversation (double-tap)
q, Ctrl+C             Quit selector
```

## 📁 Supported Providers

**Default models included:**
- **OpenAI**: GPT-5, GPT-4o, o-series
- **Anthropic**: Claude 4 Sonnet/Opus
- **DeepSeek**: R1
- **xAI**: Grok models via official API
- **Gemini**: Google's latest Pro/Flash models  
- **OpenRouter**: Access to 200+ models with flexible parameter control

*Add any model from these providers via `models.yaml` configuration.*

### Capability Matrix

| Provider | Streaming | Thinking Trace Output | Web Search |
| --- | --- | --- | --- |
| OpenAI | ✅ | ✅ (`gpt-5`, `o4-mini`, `o3`) | ❌ |
| Anthropic | ✅ | ❌ | ❌ |
| DeepSeek | ✅ | ✅ (`deepseek-reasoner`) | ❌ |
| xAI | ✅ | ❌ | ✅ (`grok-3`) |
| Gemini | ✅ | ❌ | ❌ |
| OpenRouter | ✅ | ✅ (model dependent) | ❌ |

## 🎨 Prompts

Create custom system prompts in `~/.config/llm_cli/prompts/`:

```bash
# Built-in prompts
prompt_general.txt     # Default comprehensive assistant
prompt_concise.txt     # Brief, direct responses  
prompt_empty.txt       # Minimal system message

# Custom prompts
prompt_coding.txt → llm-cli coding
prompt_creative.txt → llm-cli creative
```

Prompts load from:
1. **User config** (`~/.config/llm_cli/prompts/`) - takes precedence
2. **Package built-ins** (`src/llm_cli/prompts/`)

## 🧪 Development

### Setup

```bash
# Install with dev dependencies
uv install --group dev

# Set up pre-commit hooks
uv run pre-commit install

# Run application
uv run llm-cli
```

### Code Quality

```bash
# Type checking
uv run ty check

# Run tests
uv run pytest
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks: `uv run ty check && uv run pytest`
5. Submit a pull request

## 🏗️ Architecture

### Core Design

```
src/llm_cli/
├── core/              # Business logic
│   ├── client.py      # LLMClient - API coordination & retry
│   ├── session.py     # Chat/ChatMetadata - data models  
│   └── chat_manager.py # ChatManager - CRUD operations
├── config/            # Configuration management
│   ├── settings.py    # Config class & provider setup
│   ├── loaders.py     # YAML model configuration
│   └── user_config.py # User preference management
├── ui/                # User interface
│   ├── input_handler.py # InputHandler - prompt_toolkit
│   └── chat_selector.py # ChatSelector - interactive picker
├── providers/         # LLM provider implementations
├── renderers.py       # Response rendering (Plain/Styled)
├── registry.py        # ModelRegistry - provider management
└── response_handler.py # Streaming coordination
```

### Key Patterns

- **Provider Pattern**: Unified `LLMProvider` interface for all APIs
- **Registry Pattern**: Centralized model/provider management
- **Strategy Pattern**: Pluggable renderers and configurations
- **Observer Pattern**: Streaming response handling

### Provider Architecture

Each provider implements:
- `get_capabilities(model)` → Model feature detection
- `stream_response(messages, model, options)` → Unified streaming

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Pro tip**: Use `llm-cli --user-paths` to see all configuration locations, and customize your models in `~/.config/llm_cli/models.yaml` for personalized models, aliases and defaults.
