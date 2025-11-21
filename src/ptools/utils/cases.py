# cases: 0.0.2
import re

class Case:
    parts: list[str]
    case_type: str

    def __init__(self, parts: list[str], case_type: str):
        self.parts = parts
        self.case_type = case_type

    @staticmethod
    def from_string(s: str) -> 'Case':

        raise NotImplementedError
    def __str__(self):
        raise NotImplementedError

class CamelCase(Case):
    @staticmethod
    def from_string(s: str) -> 'CamelCase':
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
        if not len(self.parts):
          return ''
        return ''.join([self.parts[0].lower(), *[part.capitalize() for part in self.parts[1:]]])

class SnakeCase(Case):
    @staticmethod
    def from_string(s: str) -> 'SnakeCase':
        pattern = r'^[a-z]+(_[a-z0-9]+)*$'
        if not re.match(pattern, s):
            raise ValueError(f"String '{s}' is not in snake_case format")

        parts = s.split('_')
        return SnakeCase(parts=parts, case_type='snake')

    def __str__(self):
        return '_'.join(self.parts)

class KebabCase(Case):
    @staticmethod
    def from_string(s: str) -> 'KebabCase':
        pattern = r'^[a-z]+(-[a-z0-9]+)*$'
        if not re.match(pattern, s):
            raise ValueError(f"String '{s}' is not in kebab-case format")

        parts = s.split('-')
        return KebabCase(parts=parts, case_type='kebab')

    def __str__(self):
        return '-'.join(self.parts)

class PascalCase(Case):
    @staticmethod
    def from_string(s: str) -> 'PascalCase':
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
        return ''.join(part.capitalize() for part in self.parts)

class CaseResolver:
    case_classes = [CamelCase, SnakeCase, KebabCase, PascalCase]

    @staticmethod
    def resolve(s: str) -> Case:
        for case_class in CaseResolver.case_classes:
            try:
                return case_class.from_string(s)
            except ValueError:
                continue
        raise ValueError(f"String '{s}' does not match any known case format")

class CaseConverter:
    @staticmethod
    def convert(s: str, target_case: str) -> str:
        case_instance = CaseResolver.resolve(s)
        target_case_class = next((cls for cls in CaseResolver.case_classes if cls.__name__.lower() == target_case.lower() + 'case'), None)
        if not target_case_class:
            raise ValueError(f"Unsupported target case: {target_case}")
        return str(target_case_class(parts=case_instance.parts, case_type=target_case.lower()))

class CaseTest:
  @staticmethod
  def test():
    samples = {
        'camel': ['myVariableName', 'anotherExample23'],
        'snake': ['my_variable_name', 'another_example_23'],
        'kebab': ['my-variable-name', 'another-example-23'],
        'pascal': ['MyVariableName', 'AnotherExample23'],
    }

    malformed = ['myVariable_name', 'Another-Example']

    for case_type, strings in samples.items():
      for s in strings:
        case_instance = CaseResolver.resolve(s)
        assert case_instance.case_type == case_type, f"Expected {case_type}, got {case_instance.case_type}"

        for target_case in ['camel', 'snake', 'kebab', 'pascal']:
          converted = CaseConverter.convert(s, target_case)
          converted_back = CaseConverter.convert(converted, case_type)
          assert converted_back == s, f"Conversion failed: {s} -> {converted} -> {converted_back}"

    for s in malformed:
      passed = False
      try:
        case_instance = CaseResolver.resolve(s)
      except ValueError as e:
        passed = True
      assert passed, f"Malformed string '{s}' was incorrectly parsed."

cases = ['camel', 'snake', 'kebab', 'pascal']

if __name__ == "__main__":
    CaseTest.test()