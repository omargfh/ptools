from enum import Enum
from abc import ABC, abstractmethod

from .grammar import StreamTransformer, parser
from ptools.utils.decorator_compistor import DecoratorCompositor


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
    
# Output
class OutputFlavorKind(Enum):
    plain = 'plain'
    json = 'json'
    python = 'python'
    unflavored = 'unflavored'
    none = 'none'

class OutputFlavor(ABC):
    @abstractmethod
    def format(self, value):
        pass

class OutputPlainFlavor(OutputFlavor):
    def format(self, value):
        if isinstance(value, list):
            return '\n'.join(str(v) for v in value)
        elif isinstance(value, dict):
            return '\n'.join(f"{k}: {v}" for k, v in value.items())
        else:
            return str(value)
        
class OutputJSONFlavor(OutputFlavor):
    def format(self, value):
        import json
        return json.dumps(value, indent=2)

class OutputPythonFlavor(OutputFlavor):
    def format(self, value):
        return repr(value)

class OutputNoneFlavor(OutputFlavor):
    def format(self, value):
        return ''

class OutputUnflavoredFlavor(OutputFlavor):
    def format(self, value):
        return str(value)

class OutputValue:
    def __init__(self, flavor: OutputFlavorKind = OutputFlavorKind.plain):
        if flavor == OutputFlavorKind.plain:
            self.flavor = OutputPlainFlavor()
        elif flavor == OutputFlavorKind.json:
            self.flavor = OutputJSONFlavor()
        elif flavor == OutputFlavorKind.python:
            self.flavor = OutputPythonFlavor()
        elif flavor == OutputFlavorKind.none:
            self.flavor = OutputNoneFlavor()
        elif flavor == OutputFlavorKind.unflavored:
            self.flavor = OutputUnflavoredFlavor()
        else:
            raise ValueError(f"Unknown flavor: {flavor}")
            
    def format(self, value):
        return self.flavor.format(value)
   