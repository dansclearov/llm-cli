"""Constants for LLM CLI application."""

from colored import attr, fg

# UI Colors
USER_COLOR = fg("green") + attr("bold")
AI_COLOR = fg("blue") + attr("bold")
SYSTEM_COLOR = fg("violet") + attr("bold")
RESET_COLOR = attr("reset")

# Display prompts
USER_PROMPT = "User: "
AI_PROMPT = "AI: "

# Chat constants
MIN_MESSAGES_FOR_SMART_TITLE = 8
MESSAGES_PER_HISTORY_PAIR = 2
DEFAULT_MAX_HISTORY_PAIRS = 3
MAX_TITLE_LENGTH = 60

# UI Navigation
DEFAULT_PAGE_SIZE = 10
INITIAL_PAGE = 0
INITIAL_SELECTED_INDEX = 0

# Renderer Settings
USE_STYLED_RENDERER = True  # Set to False to use legacy PlainTextRenderer

# Interaction Keys
NAVIGATION_KEYS = {
    "UP": ["\x1b[A", "\x10", "k"],  # Up arrow, Ctrl+P, k
    "DOWN": ["\x1b[B", "\x0e", "j"],  # Down arrow, Ctrl+N, j
    "ENTER": ["\r", "\n"],  # Enter
    "NEXT_PAGE": ["n", "\x0c"],  # n, Ctrl+L
    "PREV_PAGE": ["p", "\x08"],  # p, Ctrl+H
    "DELETE": "d",  # First d for delete (dd to confirm)
    "QUIT": ["q", "\x03"],  # q, Ctrl+C
}