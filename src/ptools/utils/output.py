"""Output formatting utilities for ptools."""

from enum import Enum
from abc import ABC, abstractmethod

import click

from ptools.utils.decorator_compistor import DecoratorCompositor

# Output
class OutputFlavorKind(Enum):
    plain = 'plain'
    json = 'json'
    python = 'python'
    yaml = 'yaml'
    table = 'table'
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

class OutputYAMLFlavor(OutputFlavor):
    def format(self, value):
        import yaml
        return yaml.dump(value, sort_keys=False)

class OutputTableFlavor(OutputFlavor):
    def format(self, value):
        from tabulate import tabulate
        if isinstance(value, list) and all(isinstance(v, dict) for v in value):
            headers = {k: k for k in value[0].keys()}
            return tabulate(
                value, headers=headers, tablefmt="grid", maxcolwidths=50,
            )
        elif isinstance(value, dict):
            return tabulate(value.items(), tablefmt='grid', maxcolwidths=50)
        else:
            return str(value)

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
        elif flavor == OutputFlavorKind.yaml:
            self.flavor = OutputYAMLFlavor()
        elif flavor == OutputFlavorKind.table:
            self.flavor = OutputTableFlavor()
        else:
            raise ValueError(f"Unsupported output flavor: {flavor}")

    def format(self, value):
        return self.flavor.format(value)


output_flavor = DecoratorCompositor.from_list([
    click.option('--flavor', '-fv', type=click.Choice(OutputFlavorKind), default=OutputFlavorKind.plain, help='Output format flavor.'),
])
