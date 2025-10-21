from lark import Lark, Transformer, v_args

grammar =  Lark, Transformer, v_args

grammar = r"""
    ?value: number
          | quoted
          | list
          | dict
          | set
          | tuple
          | boolean
          | null
          | BAREWORD   -> str_

    BAREWORD: /.+/

    list  : "[" [value ("," value)*] "]"
    tuple : "(" [value ("," value)*] ")"
    set   : "{" [value ("," value)*] "}"
    dict  : "{" pair ("," pair)* "}"
    pair  : value ":" value

    quoted: ESCAPED_STRING
          | /'[^']*'/
          | /`[^`]*`/
          | /\"\"\".*?\"\"\"/s
          | /'''.*?'''/s

    number : SIGNED_NUMBER
    boolean: "true"i      -> true
           | "false"i     -> false
    null   : "null"i      -> null
           | "none"i      -> null

    bareword: /[A-Za-z_][A-Za-z0-9_]*/

    // comments: "#" ... or "//" ...
    COMMENT: /#[^\n]*/ | /\/\/[^\n]*/
    %ignore COMMENT

    %import common.ESCAPED_STRING
    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
"""

parser = Lark(grammar, start="value")

def either_none_or(items_nonempty, items_empty):
    """Return items_empty if items == [None], else call items_nonempty(items)."""
    def wrapper(items):
        if len(items) == 1 and items[0] is None:
            return items_empty
        return items_nonempty(items)
    return wrapper

class AttributeDict(dict):
    """Dictionary that allows access to keys as attributes."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"No such attribute: {name}")

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(f"No such attribute: {name}")


class StreamTransformer(Transformer):
    @v_args(inline=True)
    def number(self, tok):
        s = tok.value
        return float(s) if any(c in s for c in ".eE") else int(s)

    def quoted(self, tokens):
        s = tokens[0].value
        return s[1:-1]  # strip quotes/backticks

    def true(self, _): return True
    def false(self, _): return False
    def null(self, _): return None

    def list(self, items): return either_none_or(list, [])(items)
    def tuple(self, items): return either_none_or(tuple, ())(items)
    def set(self, items): return either_none_or(set, {})(items)
    def dict(self, items): return either_none_or(AttributeDict, {})(items)

    def pair(self, kv): return (kv[0], kv[1])

    @v_args(inline=True)
    def str_(self, tok):
        return tok.value