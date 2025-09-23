from lark import Lark, Transformer, Token, Tree
from ptools.utils.print import FormatUtils

GRAMMAR = r"""
// ---- start ----
start: stmt+
stmt: expr

?expr: sugar_stmt

?sugar_stmt: NAME expr
           | or_test
            
?or_test: and_test
        | or_test "or" and_test         -> c_or

?and_test: not_test
         | and_test "and" not_test      -> c_and

?not_test: "not" not_test               -> c_not
         | comparison

?comparison: bitwise_expr (COMP_OP bitwise_expr)*  -> compare
COMP_OP: "<" | "<=" | ">" | ">=" | "==" | "!=" | "="

?bitwise_expr: shift_expr
             | bitwise_expr "|" shift_expr        -> bitor
             | bitwise_expr "^" shift_expr        -> bitxor
             | bitwise_expr "&" shift_expr        -> bitand

?shift_expr: arith_expr
           | shift_expr ">>" arith_expr          -> rshift
           | shift_expr "<<" arith_expr          -> lshift

?arith_expr: term
           | arith_expr "+" term                  -> add
           | arith_expr "-" term                  -> sub

?term: term "**" factor                        -> pow
     | factor
     | term "*" factor                           -> mul
     | term "/" factor                           -> div
     | term "//" factor                          -> floordiv
     | term "%" factor                           -> mod

?factor: atom_expr

atom_expr: atom trailer*                         -> atom_expr

trailer: "." NAME                                -> attr
       | "[" slice_expr "]"                      -> subscript
       | "(" [arglist] ")"                       -> call

slice_expr: [expr] ":" [expr]                    -> slice
          | expr                                 -> index

arglist: expr ("," expr)* [","]

?atom: FSTRING                                   -> fstring
     | STRING                                    -> string
     | NUMBER                                    -> number
     | NAME                                      -> name
     | "(" expr ")"                              -> grouped
     | "{" expr "}"                    -> fcurly

// ---- tokens ----
FSTRING: /f"(?:[^"{}\\]|\\.|{[^}]*})*"/
STRING : /'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"/
NUMBER : /(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?/
NAME   : /[a-zA-Z_][a-zA-Z0-9_]*/

%import common.WS_INLINE
%ignore WS_INLINE
%ignore /#[^\n]*/      // comments
"""

# ---- Transformer: converts sugar calls to parenthesized calls and renders source ----
class SugarToParen(Transformer):
    # atoms -> return source string
    def number(self, items):
        return items[0].value

    def string(self, items):
        return items[0].value

    def fstring(self, items):
        return items[0].value
    
    def fcurly(self, items):
        return "{" + items[0] + "}"

    def name(self, items):
        return items[0].value

    def grouped(self, items):
        return "(" + items[0] + ")"

    def attr(self, items):
        obj, attr = items
        return f"{obj}.{attr}"

    def index(self, items):
        return items[0]

    def slice(self, items):
        # items: [start? , end?] length 1 or 2 depending on presence
        if len(items) == 2:
            start, end = items
            return f"{start}:{end}"
        elif len(items) == 1:
            # either start:  or :end
            text = items[0]
            if isinstance(text, str) and ":" in text:
                return text
            return text  # fallback

    def subscript(self, s):
        return f"[{s[0]}]"

    def atom_expr(self, items):
        atom = items[0]
        trailers = items[1:]
        cur = atom
        for t in trailers:
            # t is already rendered string
            if t.startswith("(") and t.endswith(")"):
                # call trailer
                cur = f"{cur}{t}"
            elif t.startswith("[") and t.endswith("]"):
                cur = f"{cur}{t}"
            elif t.startswith("."):
                cur = f"{cur}{t}"
            else:
                cur = f"{cur}{t}"
        return cur

    # trailer pieces (call produces parentheses string)
    def call(self, items):
        if not items:
            return "()"
        else:
            args = ", ".join(items[0:])  # items are already strings
            return f"({args})"

    def arglist(self, items):
        return items

    def attr(self, items):
        # coming through twice in some Lark versions; ensure proper shape
        if len(items) == 2 and isinstance(items[0], str) and isinstance(items[1], str):
            return f".{items[1]}"
        return f".{items[0]}"

    # binary ops
    def add(self, items): return f"({items[0]} + {items[1]})"
    def sub(self, items): return f"({items[0]} - {items[1]})"
    def mul(self, items): return f"({items[0]} * {items[1]})"
    def div(self, items): return f"({items[0]} / {items[1]})"
    def floordiv(self, items): return f"({items[0]} // {items[1]})"
    def mod(self, items): return f"({items[0]} % {items[1]})"
    def rshift(self, items): return f"({items[0]} >> {items[1]})"
    def lshift(self, items): return f"({items[0]} << {items[1]})"
    def bitor(self, items): return f"({items[0]} | {items[1]})"
    def bitxor(self, items): return f"({items[0]} ^ {items[1]})"
    def bitand(self, items): return f"({items[0]} & {items[1]})"
    def pow(self, items): return f"({items[0]} ** {items[1]})"
    def c_or(self, items): return f"({items[0]} or {items[1]})"
    def c_and(self, items): return f"({items[0]} and {items[1]})"
    def c_not(self, items): return f"(not {items[0]})"

    def compare(self, items):
        # items: left, op, right, op, right ...
        left = items[0]
        rest = items[1:]
        if not rest:
            return left
        parts = []
        for i in range(0, len(rest), 2):
            op = rest[i].value if isinstance(rest[i], Token) else rest[i]
            right = rest[i+1]
            parts.append(f"{op} {right}")
        return f"({left} {' '.join(parts)})"

    def stmt(self, items):
        # unwrap single child
        return items[0]

    def sugar_stmt(self, items):
        # items: [NAME, expr] — force to string
        name = items[0] if isinstance(items[0], str) else str(items[0])
        expr = items[1] if isinstance(items[1], str) else str(items[1])

        if name == 'printf' or name == 'fmt':
            if expr.startswith('f"') or expr.startswith("f'"):
                pass 
            else:
                expr = f'f"{expr}"'
                
            if name == 'fmt':
                return expr
            
        return f"{name}({expr})"
    

    def start(self, items):
        return "\n".join(str(i) for i in items)

    # sugar_call -> convert to an actual call if name is in SUGAR_FUNCS
    def sugar_call(self, items):
        name = items[0].value if isinstance(items[0], Token) else str(items[0])
        expr = items[1]
        return f"{name}({expr})"

class Parenthesizer:
    parser = Lark(GRAMMAR, parser="lalr", propagate_positions=False, maybe_placeholders=False)
    SugarToParen = SugarToParen  # configure which names get sugar treatment
    
if __name__ == "__main__":
    parser = Lark(GRAMMAR, parser="lalr", propagate_positions=False, maybe_placeholders=False)
    transformer = SugarToParen()  # configure which names get sugar treatment

    tests = {
        'a b + c * d': 'a((b + (c * d)))',
        'x and y or z': '((x and y) or z)',
        'not x or y': '((not x) or y)',
        'print x.path': 'print(x.path)',
        'print x.path[0]': 'print(x.path[0])',
        'print x.path[0:10]': 'print(x.path[0:10])',
        'print x.path[0:10].name': 'print(x.path[0:10].name)',
        'print x.path[0:10].name()': 'print(x.path[0:10].name())',
        'a b c d e': 'a(b(c(d(e))))',
        'print print x': 'print(print(x))',
        'print print x + y': 'print(print((x + y)))',
        'print (print x) + y': 'print(((print(x)) + y))',
        'print f"{x} and {y}"': 'print(f"{x} and {y}")',
        'print x, y, z': 'print(x, y, z)',
    }
    
    success_text = FormatUtils.highlight("SUCCESS", 'green')
    error_text = FormatUtils.highlight("FAILURE", 'red')

    for t, v in tests.items():
        tree = parser.parse(t)
        out = transformer.transform(tree)
        print("In: ", t)
        print("Out:", out)
        print("Matches expected:", success_text if out == v else error_text)
        print("---"*3)
