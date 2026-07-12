from enum import Enum

from ptools.utils.output import *

from .grammar import StreamTransformer, parser

# Input
class StreamValue:
    def __init__(self, text: str):
        tree = parser.parse(text)
        self.value = StreamTransformer().transform(tree)

    @staticmethod
    def Null():
        return StreamValue("null")

    def __repr__(self):
        return repr(self.value)

class InputFlavorKind(Enum):
    python_like = 'python-like'
    json = 'json'
    python = 'python'
