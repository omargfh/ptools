from prompt_toolkit.completion import Completer, Completion

class LarkCommandCompleter(Completer):
    def __init__(self, commands: list, repl_directives: list):
        self.commands = commands
        self.repl_directives = repl_directives

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        word = document.get_word_under_cursor()

        if text.endswith("@") or word.startswith("@"):
            for cmd in self.commands:
                yield Completion(f"@{cmd.name}", start_position=-len(word))
                
        if text.endswith("@/") or word.startswith("@/"):
            yield Completion("@/", start_position=-len(word))
            
        word = document.get_word_under_cursor(WORD=True)
        if word.startswith("~/") or word.startswith("./") or word.startswith("/"):
            path_completer = PathCompletion()
            yield from path_completer.get_completions(document, complete_event)
            
        if len(word) >= 2:
            for directive in self.repl_directives:
                if directive.startswith(word):
                    yield Completion(directive, start_position=-len(word))

        elif "@" in text:
            cmds = [c for c in self.commands if f"@{c.name} " in text]
            if cmds:
                last_cmd = cmds[-1]
                
                schemas = last_cmd.possible_schemas
                for schema in schemas:
                    yield Completion(repr(schema), start_position=0)
                    
                yield Completion(f"@/", start_position=-len(word))
                
class PathCompletion(Completer):
    def get_completions(self, document, complete_event):
        import os
        import glob

        text = document.text_before_cursor
        word = document.get_word_under_cursor(WORD=True)
        if not word:
            return

        # Expand user tilde
        expanded_word = os.path.expanduser(word)
        dirname = os.path.dirname(expanded_word) or "."
        prefix = os.path.basename(expanded_word)
        
        try:
            entries = glob.glob(os.path.join(dirname, prefix) + "*")
            for entry in entries:
                display = os.path.relpath(entry)
                if os.path.isdir(entry):
                    display += "/"
                
                completion = display
                if not display.startswith('./') and not display.startswith('../'):
                    completion = './' + display
                yield Completion(completion, display=display, start_position=-len(word))
        except Exception:
            pass