# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Testing:**
```bash
pytest                    # Run all tests
pytest tests/test_main.py # Run specific test file
```

**Code Quality:**
```bash
black .                   # Format code
isort .                   # Sort imports
mypy .                    # Type checking
```

**Installation & Setup:**
```bash
# Local development with uv
uv install

# Install dev dependencies
uv install --group dev

# Add new dependencies
uv add <package-name>     # Add a new dependency

# Global installation
pipx install -e .         # Install from local copy
pipx install --force -e . # Reinstall after changes
```

**Running the application:**
```bash
llm-cli                   # CLI interface with default settings
llm-cli concise -m sonnet # Use specific prompt and model
```

## Architecture Overview

**Multi-provider LLM Client:**
Supports OpenAI, Anthropic, DeepSeek, Google Gemini, and xAI through a unified interface.

**Centralized Model Registry:**
- `ModelRegistry` loads all models and aliases from `models.yaml` 
- Providers are "dumb" API clients - no hardcoded model definitions
- Default model configurable via `aliases.default` in YAML
- Cross-provider aliases supported

**Provider Implementations:**
- OpenAI/xAI: Standard chat completions API
- DeepSeek: Streams reasoning traces separately before main response  
- Anthropic: Uses system messages separately from conversation
- Gemini: Converts OpenAI format to Gemini's content structure

**Model Configuration:**
- **Single source of truth**: `models.yaml` contains all models, capabilities, and aliases
- Per-model settings: max_tokens, supports_search, supports_thinking
- User can override with `~/.config/llm_cli/models.yaml`

**Configuration & Prompts:**
Dual-location system:
1. User config directory (`~/.config/llm_cli/prompts/`) - takes precedence
2. Package built-in prompts (`src/llm_cli/prompts/`)

Format: `prompt_[name].txt`, loaded via `utils.py:read_system_message_from_file()`

**Chat Management:**
- Rich-based interactive chat selection 
- Automatic session persistence with metadata
- Smart title generation (triggers after 8+ messages)
- Auto-save functionality

**Streaming & Output:**
- Two renderers: `PlainTextRenderer` and `StyledRenderer` 
- `StyledRenderer` provides styled thinking traces (NOT markdown rendering!)
- Rich console with `highlight=False` to prevent number styling in LLM output
- Real-time streaming with interrupt handling

**Code Organization:**
- `ModelRegistry` (registry.py) - Central model/provider management
- `LLMClient` (main.py) - High-level API client with retry logic
- `ChatManager` (chat_manager.py) - Session persistence
- `ResponseHandler` (response_handler.py) - Streaming coordination
- `StyledRenderer`/`PlainTextRenderer` (renderers.py) - Output formatting

**Main Function Structure:**
Broken into logical functions:
- `parse_arguments()` - CLI parsing
- `setup_configuration()` - Component setup  
- `handle_chat_selection()` - Chat loading
- `create_new_chat()` - New session creation
- `run_chat_loop()` - Main interaction
- `main()` - High-level orchestration

**Key Constants:**
- `MIN_MESSAGES_FOR_SMART_TITLE = 8`
- `DEFAULT_PAGE_SIZE = 10` 
- `DEFAULT_MAX_HISTORY_PAIRS = 3`

**Common Gotchas:**
1. Add models to `models.yaml`, not provider classes
2. `StyledRenderer` != markdown rendering, just styled console output
3. Default model from YAML `aliases.default`, not hardcoded
4. Providers don't define their own models anymore
5. Rich console has `highlight=False` to prevent auto-styling numbers
6. `utils.py` mixes concerns (prompts + model config) - organizational debt

**Quick Tests:**
```bash
uv run llm-cli --help   # Smoke test
uv run python -c "from src.llm_cli.config import setup_providers; print(list(setup_providers().get_available_models().keys()))"  # Test model loading
```