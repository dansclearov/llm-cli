from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.cursor_shapes import ModalCursorShapeConfig

from llm_cli.constants import USER_PROMPT


class InputHandler:
    def __init__(self, config=None):
        self.config = config
    
    def get_user_input(self) -> str:
        """Get user input with Shift+Enter (or Ctrl+J) for new lines."""
        bindings = KeyBindings()
        
        @bindings.add('c-m')  # Enter key
        def _(event):
            # Submit the input
            event.app.exit(result=event.app.current_buffer.text)
        
        @bindings.add('c-j')  # Ctrl+J acts as Shift+Enter for newline
        def _(event):
            # Ctrl+J sends ASCII 0x0A (LF), same as Shift+Enter in most terminals
            # This provides a portable way to insert newlines across Unix/Linux/macOS
            event.app.current_buffer.insert_text('\n')
            
        @bindings.add('c-c')  # Ctrl+C
        def _(event):
            # Exit cleanly without greying out
            event.app.exit(exception=KeyboardInterrupt)
            
        try:
            # Get input with prompt_toolkit
            vim_mode = self.config.vim_mode if self.config else False
            cursor_config = ModalCursorShapeConfig() if vim_mode else None
            user_input = prompt(
                HTML(f"<ansigreen><b>{USER_PROMPT}</b></ansigreen>"),
                multiline=True,
                key_bindings=bindings,
                prompt_continuation=lambda width, line_number, is_soft_wrap: "",
                vi_mode=vim_mode,
                cursor=cursor_config,
            )
            return user_input.strip()
        except KeyboardInterrupt:
            raise
        except EOFError:
            # Handle Ctrl+D
            raise KeyboardInterrupt()