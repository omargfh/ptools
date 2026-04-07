"""Pygments lexer used to syntax-highlight the LLM REPL prompt input."""
from pygments.lexer import RegexLexer
from pygments.token import Keyword, Name, String, Text

__version__ = "0.1.0"


def make_lexer_from_lark():
    """Build a Pygments :class:`RegexLexer` matching the ptools-llm command grammar."""
    return type(
        "LarkCommandLexer",
        (RegexLexer,),
        {
            "tokens": {
                "root": [
                    (r"@[a-zA-Z_][a-zA-Z0-9_]*", Keyword),         # COMMAND
                    (r"@/", Keyword),                              # COMMAND_DELIMITER
                    (r"[a-zA-Z_][a-zA-Z0-9_]*=", Name.Attribute),  # kwarg names
                    (r'"[^"]*"|\'[^\']*\'|`[^`]*`', String),       # string args
                    (r"[^@,\s]+", Name),                           # values
                    (r"\s+", Text),
                ]
            }
        }
    )

LarkCommandLexer = make_lexer_from_lark()
