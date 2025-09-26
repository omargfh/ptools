import threading
import time
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings

from ptools.utils.print import FormatUtils

from ..prompt import parse_prompt

from .lexer import LarkCommandLexer
from .intellisense import LarkCommandCompleter

QMARK = FormatUtils.highlight("?", "green")
ON = FormatUtils.highlight("on", "green")
OFF = FormatUtils.highlight("off", "red")
DIRECTIVE = lambda x: FormatUtils.highlight(x, "yellow")

    
multiline_mode = {"enabled": False}  # mutable container so we can toggle inside handler

kb = KeyBindings()

@kb.add("f4")
def _(event):
    multiline_mode["enabled"] = not multiline_mode["enabled"]

@kb.add("tab")
def _(event):
    buffer = event.current_buffer
    if buffer.complete_state:
        buffer.complete_state = None
        buffer.start_completion(select_first=False)
    else:
        buffer.start_completion(select_first=True)

def start_chat(
    commands,
    user_style="bold yellow",
    assistant_color="blue",
    exit_commands=("/exit", "/quit", 'quit', 'exit', 'quit()'),
    on_user_message=lambda msg: None,
    history=[],
):
    """Start an interactive chat session."""
    print("\033c", end="")
    styled_assistant_prompt = FormatUtils.highlight("> Assistant: ", assistant_color)
    
    if len(history) > 0:
        print(FormatUtils.background("Previous messages ", "yellow"))
    for message in history:
        role = message.role
        content = message.content
        if role == 'user':
            print(FormatUtils.highlight("> You: ", 'yellow'), end='')
            print(content, end='' if content.endswith('\n') else '\n')

        elif role == 'assistant':
            print(styled_assistant_prompt, end='')
            print(content, end='' if content.endswith('\n') else '\n')
    if len(history) > 0:
        print(FormatUtils.background("End of previous messages ", "yellow"))
        print()

    
    repl_directives = exit_commands + ("/ml",)
    multiline = multiline_mode["enabled"]
    bottom_toolbar = lambda: f"F4: Toggle Multiline Mode ({'ON' if multiline_mode['enabled'] else 'OFF'})" + \
        f" | Type /exit or /quit to leave. Type /help for commands."
    session = PromptSession(
        lexer=PygmentsLexer(LarkCommandLexer),
        completer=LarkCommandCompleter(commands, repl_directives),
        history=InMemoryHistory(history),
        style=Style.from_dict({
            "pygments.keyword":        "bold ansicyan",   # commands like @file, @greet
            "pygments.name.attribute": "ansiyellow",      # kwarg names (foo=)
            "pygments.string":         "ansigreen",       # "quoted values"
            "pygments.name":           "ansicyan",        # positional args
            "pygments.text":           "",                # leave whitespace default
            "prompt":                  user_style,       # prompt label itself (> )
        }),
        key_bindings=kb,
        bottom_toolbar=bottom_toolbar,
    )

    while True:
        multiline = multiline_mode["enabled"]
        try:
            prompt_char = ">>>" if multiline else ">"
            user_prompt_styled = f"{prompt_char} You: "
            user_input = session.prompt(user_prompt_styled, multiline=multiline)

            if not user_input.strip():
                continue
            elif user_input.strip() in exit_commands:
                print(FormatUtils.highlight("? ", "green") + "Exiting chat.")
                break
            elif user_input.strip() == "/help":
                print(FormatUtils.highlight("? ", "green") + "Available commands:")
                for cmd in commands:
                    print(f"  {FormatUtils.bold(cmd.name)}: {cmd.description}")
                    for schema in cmd.possible_schemas: 
                        print(f"    @{cmd.name} {repr(schema)} @/")
                        
                continue

            user_message = parse_prompt(user_input)
            print(f"{styled_assistant_prompt}", end='', flush=True)

            spinner = Spinner(prefix=styled_assistant_prompt)
            spinner.start()

            seen_first_chunk = False
            response = on_user_message(user_message)
            for chunk in response:
                if not seen_first_chunk:
                    seen_first_chunk = True
                    spinner.stop()
                    print(f"{styled_assistant_prompt}", end='', flush=True)
                print(chunk, end='', flush=True)



        except KeyboardInterrupt:
            continue
        except EOFError:
            break
            
        
class Spinner():
    def __init__(self, prefix):
        self.spinner = ["|", "/", "-", "\\"]
        self.i = 0
        self.stop_spinner = False
        self.thread = threading.Thread(target=self.spin, daemon=True)
        self.prefix = prefix

    def start(self):
        self.stop_spinner = False
        self.thread.start()

    def stop(self):
        self.stop_spinner = True
        self.thread.join()
        sys.stdout.write("\r" + " " * 20 + "\r")  # Clear the spinner line
        sys.stdout.flush()

    def spin(self):
        while not self.stop_spinner:
            sys.stdout.write(f"\r{self.prefix} {self.spinner[self.i % len(self.spinner)]}")
            sys.stdout.flush()
            self.i += 1
            time.sleep(0.1)