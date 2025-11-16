# LLM-CLI

A multi-provider command-line interface for interacting with large language models. Features rich terminal UI, comprehensive chat management, and unified streaming responses across providers.

![Demo](demo.gif)

## ✨ Features

- **Multi-provider support**: OpenAI, Anthropic, Gemini, OpenRouter (DeepSeek, xAI Grok, Qwen), Moonshot (Kimi)
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
GEMINI_API_KEY=your_gemini_api_key
MOONSHOTAI_API_KEY=your_moonshot_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

### Model Configuration

Models are centrally configured in `src/llm_cli/models.yaml` with user overrides at `~/.config/llm_cli/models.yaml`:

```yaml
aliases:
  default: sonnet                    # Default CLI model (alias)
  sonnet: anthropic/claude-sonnet-4-5-20250929
  opus: anthropic/claude-opus-4-1-20250805
  gpt-4o: openai/chatgpt-4o-latest
  gpt-4.5: openai/gpt-4.5-preview
  gpt-5: openai-responses/gpt-5
  r1: openrouter/deepseek/deepseek-r1-0528
  r1-free: "openrouter/deepseek/deepseek-r1-0528:free"
  kimi: moonshotai/kimi-latest
  kimi-thinking: moonshotai/kimi-k2-thinking
  qwen3-max: openrouter/qwen/qwen3-max
  grok-4: openrouter/x-ai/grok-4

anthropic:
  claude-sonnet-4-5-20250929:
    supports_search: true
    supports_thinking: true
    max_tokens: 8192

openai-responses:
  gpt-5:
    supports_search: true
    supports_thinking: true

google-gla:                      # Gemini
  gemini-2.5-pro:
    supports_search: true
    supports_thinking: true

_openrouter_min_fp8: &openrouter_min_fp8
  provider:
    quantizations: ["fp8", "fp16", "bf16", "fp32", "unknown"]

openrouter:
  "deepseek/deepseek-r1-0528:free":
    supports_search: true
    supports_thinking: true
    extra_params:
      <<: *openrouter_min_fp8

  deepseek/deepseek-r1-0528:
    supports_search: true
    supports_thinking: true
    extra_params:
      <<: *openrouter_min_fp8

  x-ai/grok-4:
    supports_search: true

  qwen/qwen3-max:
    supports_search: true
    extra_params:
      <<: *openrouter_min_fp8

moonshotai:
  kimi-latest:
    supports_search: false   # Moonshot provider doesn't expose the built-in WebSearchTool

  kimi-k2-thinking:
    supports_search: false
    supports_thinking: true
```

Reasoning-focused OpenAI models (e.g., `gpt-5`, `o3`, `o4-mini`) should live under the `openai-responses` provider section so Pydantic AI routes them through the Responses API and can surface their thinking traces. Likewise, Gemini models should be listed under `google-gla`/`google-vertex`, xAI/DeepSeek via OpenRouter should stay under `openrouter`, and Kimi models should use the `moonshotai` provider so the right client (and associated features like thinking/search) is used.

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

### Thinking Traces

- When thinking mode is enabled, OpenAI reasoning models automatically receive `openai_reasoning_summary=detailed` and `openai_reasoning_effort=medium` so the CLI can show their reasoning summaries (OpenAI does not expose raw CoT tokens).
- Anthropic models automatically get `anthropic_thinking` enabled with a default `budget_tokens=2048`, satisfying the API requirement while giving you useful insight.
- Google Gemini models automatically receive `google_thinking_config={'include_thoughts': True}` so their thinking traces stream into the CLI.
- You can further customize provider-specific knobs via `ChatOptions.extra_settings` if you need different defaults.

### Web Search (`--search`)

- When `--search` is passed, we attach Pydantic AI's native `WebSearchTool` for providers that support first-party search (Anthropic, OpenAI Responses models such as `gpt-5`, Google Gemini). Moonshot's OpenAI-compatible API does not expose this hook via pydantic-ai yet.
- OpenRouter models automatically add the platform's `web` plugin and switch to their `:online` variant so search works there too.
- Providers without a dedicated search hook simply ignore the flag (you'll see a short warning only if you explicitly enable it on an unsupported model).

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
- **OpenAI**: GPT-4o, GPT-4.5 preview, GPT-5 (Responses API for thinking/search)
- **Anthropic**: Claude 4.5 Sonnet, Claude 4.1 Opus
- **Gemini**: 2.5 Pro/Flash
- **Moonshot**: Kimi Latest, Kimi Thinking Preview
- **OpenRouter**: DeepSeek R1 (free/paid), xAI Grok-4, Qwen3 Max

*Add any model from these providers via `models.yaml` configuration.*

### Capability Matrix

| Provider | Streaming | Thinking Trace Output | Web Search |
| --- | --- | --- | --- |
| OpenAI Responses (o-/gpt-5) | ✅ | ✅ | ✅ |
| OpenAI Chat (gpt-4o, 4.5) | ✅ | ⚠️ (model-limited) | ⚠️ (no built-in hook) |
| Anthropic | ✅ | ✅ | ✅ |
| Gemini | ✅ | ✅ | ✅ |
| Moonshot (Kimi) | ✅ | ✅ (thinking model) | ⚠️ (no built-in hook) |
| OpenRouter (R1, Grok, Qwen) | ✅ | ✅ | ✅* |

\*OpenRouter search uses the platform `web` plugin + `:online` model variant.

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
├── llm_types.py       # Shared capability + option dataclasses
├── renderers.py       # Response rendering (Plain/Styled)
├── registry.py        # ModelRegistry - alias management
└── response_handler.py # Streaming coordination
```

### Key Patterns

- **Pydantic AI**: Direct access to OpenAI/Anthropic/Gemini/etc via `pydantic_ai.direct`
- **Registry Pattern**: Centralized alias + capability management
- **Strategy Pattern**: Pluggable renderers and configurations
- **Observer Pattern**: Streaming response handling

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Pro tip**: Use `llm-cli --user-paths` to see all configuration locations, and customize your models in `~/.config/llm_cli/models.yaml` for personalized models, aliases and defaults.
