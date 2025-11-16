# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Testing:**
```bash
uv run pytest                    # Run all tests
uv run pytest tests/test_main.py # Run specific test file
```

**Code Quality:**
```bash
uv run ty check           # Type checking (ruff formatting/linting handled by pre-commit)
```

**Installation & Setup:**
```bash
# Local development with uv
uv install

# Install dev dependencies
uv install --group dev

# Set up pre-commit hooks
uv run pre-commit install

# Add new dependencies
uv add <package-name>     # Add a new dependency

# Global installation
pipx install -e .         # Install from local copy
pipx install --force -e . # Reinstall after changes
```

**Running the application:**
```bash
uv run llm-cli                   # CLI interface with default settings
uv run llm-cli concise -m sonnet # Use specific prompt and model
```

## Architecture Overview (Post-Refactoring)

**Directory Structure:**
```
src/llm_cli/
├── core/              # Core business logic
│   ├── client.py      # LLMClient - API calls & retry logic
│   ├── session.py     # Chat & ChatMetadata - data models
│   └── chat_manager.py # ChatManager - CRUD operations
├── config/            # Configuration management
│   ├── settings.py    # Config class & registry setup
│   ├── loaders.py     # YAML model configuration loading
│   └── user_config.py # User configuration management
├── ui/                # User interface components
│   ├── input_handler.py # InputHandler - prompt_toolkit integration
│   └── chat_selector.py # ChatSelector - interactive chat picker
├── llm_types.py       # Shared chat/model capability dataclasses
├── app.py             # Main application orchestration
├── cli.py             # Command-line argument parsing
├── main.py            # Entry point (delegates to app.py)
├── constants.py       # All constants & UI config
├── exceptions.py      # Custom exception classes
├── prompts.py         # Prompt file loading
├── model_config.py    # Model capabilities loading
├── registry.py        # ModelRegistry - alias + capability management
└── renderers.py       # Response rendering (PlainTextRenderer, StyledRenderer)
```

**Multi-provider LLM Client:**
Supports OpenAI, Anthropic, DeepSeek, Google Gemini, xAI, and OpenRouter through Pydantic AI's `direct` APIs with a unified interface.

**Centralized Model Registry:**
- `ModelRegistry` loads all models and aliases from `models.yaml` 
- Providers are "dumb" API clients - no hardcoded model definitions
- Default model configurable via `aliases.default` in YAML
- Cross-provider aliases supported

**Model Configuration:**
- **Single source of truth**: `models.yaml` contains all models, capabilities, and aliases
- Per-model settings: max_tokens, supports_search, supports_thinking
- User can override with `~/.config/llm_cli/models.yaml`

**Configuration & Prompts:**
Dual-location system:
1. User config directory (`~/.config/llm_cli/prompts/`) - takes precedence
2. Package built-in prompts (`src/llm_cli/prompts/`)

Format: `prompt_[name].txt`, loaded via `prompts.py:read_system_message_from_file()`

**Chat Management:**
- Rich-based interactive chat selection via `ui/chat_selector.py`
- Automatic session persistence with metadata in `core/session.py`
- Smart title generation (triggers after 8+ messages)
- Auto-save functionality

**Streaming & Output:**
- Two renderers: `PlainTextRenderer` and `StyledRenderer` 
- `StyledRenderer` provides styled thinking traces (NOT markdown rendering!)
- Rich console with `highlight=False` to prevent number styling in LLM output
- Real-time streaming with interrupt handling

**Key Components:**
- `LLMClient` (core/client.py) - High-level API client with retry logic
- `ChatManager` (core/chat_manager.py) - Session persistence & management
- `Chat`/`ChatMetadata` (core/session.py) - Data models
- `ChatSelector` (ui/chat_selector.py) - Interactive chat selection
- `InputHandler` (ui/input_handler.py) - User input handling
- `ModelRegistry` (registry.py) - Central model/provider management
- `ResponseHandler` (response_handler.py) - Streaming coordination

**Main Function Structure:**
Located in `app.py`, broken into logical functions:
- `parse_arguments()` - CLI parsing (from cli.py)
- `setup_configuration()` - Component setup  
- `handle_chat_selection()` - Chat loading
- `create_new_chat()` - New session creation
- `run_chat_loop()` - Main interaction
- `main()` - High-level orchestration

**Key Constants:**
All centralized in `constants.py`:
- `MIN_MESSAGES_FOR_SMART_TITLE = 8`
- `DEFAULT_PAGE_SIZE = 10` 
- `DEFAULT_MAX_HISTORY_PAIRS = 3`
- `USER_PROMPT = "User: "`
- `AI_PROMPT = "AI: "`
- UI colors and navigation keys

**Common Gotchas:**
1. Add models to `models.yaml`, not provider classes
2. `StyledRenderer` != markdown rendering, just styled console output
3. Default model from YAML `aliases.default`, not hardcoded
4. No bespoke provider classes—add/update models via YAML aliases instead
5. Thinking traces:
   - OpenAI reasoning models automatically receive `openai_reasoning_summary="detailed"` when thinking is enabled so we can render their reasoning summaries.
   - OpenAI reasoning models also set `openai_reasoning_effort="medium"` by default to satisfy the API requirement.
   - Anthropic models automatically get `anthropic_thinking={"type": "enabled", "budget_tokens": 2048}` when thinking is enabled to satisfy the API requirement.
   - Google Gemini models default to `google_thinking_config={"include_thoughts": True}` when thinking is enabled so their thoughts stream into the UI.
6. Reasoning-focused OpenAI models (gpt-5, o-series) should be defined under the `openai-responses` provider section so the Responses API (with thinking traces) is used.
7. `--search` wires up Pydantic AI’s `WebSearchTool` only for providers that support it (OpenAI Responses, Anthropic, Gemini). OpenRouter models automatically switch to their `:online` variant and add the `web` plugin so search works there too; other providers simply ignore the flag.
8. Rich console has `highlight=False` to prevent auto-styling numbers
9. Prompts loaded from `src/llm_cli/prompts/` directory, not a Python package
10. Custom exceptions in `exceptions.py` for proper error handling

**Quick Tests:**
```bash
uv run llm-cli --help   # Smoke test
uv run python -c "from src.llm_cli.config.settings import setup_providers; print(list(setup_providers().get_available_models().keys()))"  # Test model loading
```
