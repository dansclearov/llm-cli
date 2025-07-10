from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings

from llm_cli.constants import USER_PROMPT


class InputHandler:
    def __init__(self, config=None):
        self.config = config
    
    def get_user_input(self) -> str:
        """Get user input with shift+enter for new lines."""
        bindings = KeyBindings()
        
        @bindings.add('c-m')  # Enter key
        def _(event):
            # Submit the input
            event.app.exit(result=event.app.current_buffer.text)
        
        @bindings.add('c-j')  # Ctrl+J / Shift+Enter for newline
        def _(event):
            # Just add a plain newline
            event.app.current_buffer.insert_text('\n')
            
        @bindings.add('c-c')  # Ctrl+C
        def _(event):
            # Exit cleanly without greying out
            event.app.exit(exception=KeyboardInterrupt)
            
        try:
            # Get input with prompt_toolkit
            vim_mode = self.config.vim_mode if self.config else False
            user_input = prompt(
                HTML(f"<ansigreen><b>{USER_PROMPT}</b></ansigreen>"),
                multiline=True,
                key_bindings=bindings,
                prompt_continuation=lambda width, line_number, is_soft_wrap: "",
                vi_mode=vim_mode,
            )
            return user_input.strip()
        except KeyboardInterrupt:
            raise
        except EOFError:
            # Handle Ctrl+D
            raise KeyboardInterrupt()