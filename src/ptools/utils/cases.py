"""Case format utilities for ptools.
Provides classes and functions to handle different case formats
(camelCase, snake_case, kebab-case, PascalCase), including parsing from strings,
converting between formats, and resolving the case format of a given string.

:version: 0.2.2
"""
import re

__version__ = "0.2.2"


class Case:
    """Base class for different case formats.

    :param parts: The lower-cased word parts that compose the identifier.
    :param case_type: A short label identifying the concrete case format
        (``"camel"``, ``"snake"``, ``"kebab"``, ``"pascal"``).
    """
    parts: list[str]
    case_type: str

    def __init__(self, parts: list[str], case_type: str):
        self.parts = parts
        self.case_type = case_type

    @staticmethod
    def from_string(s: str) -> 'Case':
        """Parse ``s`` into a :class:`Case` instance. Implemented by subclasses."""
        raise NotImplementedError

    def __str__(self):
        """Render the case parts back into a single string. Implemented by subclasses."""
        raise NotImplementedError

class CamelCase(Case):
    """camelCase format, e.g. 'myVariableName'."""
    @staticmethod
    def from_string(s: str) -> 'CamelCase':
        """Parse ``s`` as camelCase, raising :class:`ValueError` if it does not match."""
        pattern = r'^[a-z][a-zA-Z0-9]*$'
        if not re.match(pattern, s):
            raise ValueError(f"String '{s}' is not in CamelCase format")

        parts = []
        current = ''
        for char in s:
            if char.isupper() and current:
                parts.append(current)
                current = char.lower()
            else:
                current += char.lower()
        if current:
            parts.append(current)
        return CamelCase(parts=parts, case_type='camel')

    def __str__(self):
        """Render the parts as camelCase."""
        if not len(self.parts):
          return ''
        return ''.join([self.parts[0].lower(), *[part.capitalize() for part in self.parts[1:]]])

class SnakeCase(Case):
    """snake_case format, e.g. 'my_variable_name'."""
    @staticmethod
    def from_string(s: str) -> 'SnakeCase':
        """Parse ``s`` as snake_case, raising :class:`ValueError` if it does not match."""
        pattern = r'^[a-z]+(_[a-z0-9]+)*$'
        if not re.match(pattern, s):
            raise ValueError(f"String '{s}' is not in snake_case format")

        parts = s.split('_')
        return SnakeCase(parts=parts, case_type='snake')

    def __str__(self):
        """Render the parts as snake_case."""
        return '_'.join(self.parts)

class KebabCase(Case):
    """kebab-case format, e.g. 'my-variable-name'."""
    @staticmethod
    def from_string(s: str) -> 'KebabCase':
        """Parse ``s`` as kebab-case, raising :class:`ValueError` if it does not match."""
        pattern = r'^[a-z]+(-[a-z0-9]+)*$'
        if not re.match(pattern, s):
            raise ValueError(f"String '{s}' is not in kebab-case format")

        parts = s.split('-')
        return KebabCase(parts=parts, case_type='kebab')

    def __str__(self):
        """Render the parts as kebab-case."""
        return '-'.join(self.parts)

class PascalCase(Case):
    """PascalCase format, e.g. 'MyVariableName'."""
    @staticmethod
    def from_string(s: str) -> 'PascalCase':
        """Parse ``s`` as PascalCase, raising :class:`ValueError` if it does not match."""
        pattern = r'^[A-Z][a-zA-Z0-9]*$'
        if not re.match(pattern, s):
            raise ValueError(f"String '{s}' is not in PascalCase format")

        parts = []
        current = ''
        for char in s:
            if char.isupper() and current:
                parts.append(current)
                current = char.lower()
            else:
                current += char.lower()
        if current:
            parts.append(current)
        return PascalCase(parts=parts, case_type='pascal')

    def __str__(self):
        """Render the parts as PascalCase."""
        return ''.join(part.capitalize() for part in self.parts)

class CaseResolver:
    """Utility to resolve a string to its corresponding case format."""
    case_classes = [CamelCase, SnakeCase, KebabCase, PascalCase]

    @staticmethod
    def resolve(s: str) -> Case:
        """Return a :class:`Case` instance for ``s`` by trying each known format.

        :raises ValueError: if ``s`` does not match any known case format.
        """
        for case_class in CaseResolver.case_classes:
            try:
                return case_class.from_string(s)
            except ValueError:
                continue
        raise ValueError(f"String '{s}' does not match any known case format")

class CaseConverter:
    """Utility to convert strings between different case formats."""
    @staticmethod
    def convert(s: str, target_case: str) -> str:
        """Convert ``s`` from its detected case format into ``target_case``.

        :param s: The input identifier in any supported case format.
        :param target_case: One of ``"camel"``, ``"snake"``, ``"kebab"``,
            ``"pascal"``.
        :returns: ``s`` rewritten in the target case format.
        :raises ValueError: if ``s`` cannot be parsed or ``target_case`` is unknown.
        """
        case_instance = CaseResolver.resolve(s)
        target_case_class = next((cls for cls in CaseResolver.case_classes if cls.__name__.lower() == target_case.lower() + 'case'), None)
        if not target_case_class:
            raise ValueError(f"Unsupported target case: {target_case}")
        return str(target_case_class(parts=case_instance.parts, case_type=target_case.lower()))