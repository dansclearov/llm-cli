# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Testing:**
```bash
pytest                    # Run all tests
pytest tests/test_main.py # Run specific test file
```

**Installation & Setup:**
```bash
# Local development with uv
uv install

# Global installation
pipx install -e .         # Install from local copy
pipx install --force -e . # Reinstall after changes
```

**Running the application:**
```bash
llm-cli                   # CLI interface with default settings
llm-cli concise -m sonnet # Use specific prompt and model
llm-cli-app              # Gradio web interface (requires gradio dependency)
```

## Architecture Overview

**Multi-provider LLM Client:**
The application supports multiple LLM providers through a unified interface:
- OpenAI (GPT-4o, GPT-4.5, O3, O4-mini)
- Anthropic (Claude Sonnet, Opus)
- DeepSeek (R1 with reasoning traces)
- Google (Gemini 2.5 Pro/Flash)
- xAI (Grok-3)

**Provider-specific implementations:**
- OpenAI/xAI: Standard chat completions API
- DeepSeek: Streams reasoning content separately before main response
- Anthropic: Uses system messages separately from conversation
- Gemini: Converts OpenAI format to Gemini's content structure

**Configuration & Prompts:**
The system uses a dual-location prompt system:
1. User config directory (`~/.config/llm_cli/prompts/`) - takes precedence
2. Package built-in prompts (`src/llm_cli/prompts/`)

Prompts follow the format `prompt_[name].txt` and are loaded via `utils.py:read_system_message_from_file()`.

**Chat History Management:**
- JSON-based persistence with automatic temp file backup
- Supports save/load/append operations via special `%` commands
- System messages are filtered when appending to avoid conflicts
- Pagination for viewing long conversation histories

**Streaming Architecture:**
All providers implement streaming responses with provider-specific handling:
- Retry logic with exponential backoff using `tenacity`
- Real-time output display during streaming
- Consistent error handling across providers

**Dual Interface:**
- CLI (`main.py`): Direct terminal interaction with full feature set
- Web (`app.py`): Gradio interface with simplified model/prompt selection

**Model Mappings:**
Model names are abstracted through `constants.py:MODEL_MAPPINGS` to provide user-friendly aliases for actual API model identifiers.