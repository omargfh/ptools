"""Tests for ptools.utils.cases - case-style parsing and conversion."""
import pytest

from ptools.utils.cases import (
    CamelCase,
    CaseConverter,
    CaseResolver,
    KebabCase,
    PascalCase,
    SnakeCase,
)


class TestCamelCase:
    def test_parses_simple_camel(self):
        c = CamelCase.from_string("myVariableName")
        assert c.parts == ["my", "variable", "name"]
        assert c.case_type == "camel"
        assert str(c) == "myVariableName"

    def test_parses_single_word(self):
        c = CamelCase.from_string("hello")
        assert c.parts == ["hello"]
        assert str(c) == "hello"

    def test_with_digits(self):
        c = CamelCase.from_string("anotherExample23")
        assert str(c) == "anotherExample23"

    def test_rejects_pascal(self):
        with pytest.raises(ValueError):
            CamelCase.from_string("MyVariable")

    def test_rejects_snake(self):
        with pytest.raises(ValueError):
            CamelCase.from_string("my_var")


class TestSnakeCase:
    def test_parses(self):
        s = SnakeCase.from_string("my_variable_name")
        assert s.parts == ["my", "variable", "name"]
        assert str(s) == "my_variable_name"

    def test_rejects_upper(self):
        with pytest.raises(ValueError):
            SnakeCase.from_string("My_Var")


class TestKebabCase:
    def test_parses(self):
        k = KebabCase.from_string("my-variable-name")
        assert k.parts == ["my", "variable", "name"]
        assert str(k) == "my-variable-name"

    def test_rejects_mixed(self):
        with pytest.raises(ValueError):
            KebabCase.from_string("My-Var")


class TestPascalCase:
    def test_parses(self):
        p = PascalCase.from_string("MyVariableName")
        assert p.parts == ["my", "variable", "name"]
        assert str(p) == "MyVariableName"

    def test_rejects_camel(self):
        with pytest.raises(ValueError):
            PascalCase.from_string("myVariable")


class TestCaseResolver:
    @pytest.mark.parametrize(
        "text,expected_type",
        [
            ("myVariableName", "camel"),
            ("my_variable_name", "snake"),
            ("my-variable-name", "kebab"),
            ("MyVariableName", "pascal"),
        ],
    )
    def test_resolve(self, text, expected_type):
        assert CaseResolver.resolve(text).case_type == expected_type

    @pytest.mark.parametrize("bad", ["myVariable_name", "Another-Example", "has spaces"])
    def test_unresolvable_raises(self, bad):
        with pytest.raises(ValueError):
            CaseResolver.resolve(bad)


class TestCaseConverter:
    @pytest.mark.parametrize(
        "src,target,expected",
        [
            ("myVariableName", "snake", "my_variable_name"),
            ("my_variable_name", "camel", "myVariableName"),
            ("my_variable_name", "pascal", "MyVariableName"),
            ("my-variable-name", "snake", "my_variable_name"),
            ("MyVariableName", "kebab", "my-variable-name"),
        ],
    )
    def test_direct_conversion(self, src, target, expected):
        assert CaseConverter.convert(src, target) == expected

    @pytest.mark.parametrize("source", ["myVar", "my_var", "my-var", "MyVar"])
    @pytest.mark.parametrize("target", ["camel", "snake", "kebab", "pascal"])
    def test_roundtrip(self, source, target):
        original_type = CaseResolver.resolve(source).case_type
        converted = CaseConverter.convert(source, target)
        back = CaseConverter.convert(converted, original_type)
        assert back == source

    def test_unsupported_target(self):
        with pytest.raises(ValueError):
            CaseConverter.convert("my_var", "screaming")
