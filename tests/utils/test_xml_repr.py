"""Tests for ptools.utils.xml_repr - XML representation helpers."""
from ptools.utils.xml_repr import XMLRepr, xmlclass


class TestXMLRepr:
    def test_self_closing_when_no_children(self):
        class Foo:
            pass

        repr_ = XMLRepr(Foo(), [], id="1", name="foo")
        out = repr_.__xml__()
        assert out.startswith("<Foo ")
        assert out.endswith("/>")
        assert 'id="1"' in out
        assert 'name="foo"' in out

    def test_attrs_camel_cased(self):
        class Node:
            pass

        repr_ = XMLRepr(Node(), [], my_attr="x")
        out = repr_.__xml__()
        assert 'myAttr="x"' in out

    def test_callable_attr_values(self):
        class Node:
            pass

        repr_ = XMLRepr(Node(), [], dynamic=lambda: "hello")
        out = repr_.__xml__()
        assert 'dynamic="hello"' in out

    def test_string_child(self):
        class Node:
            pass

        repr_ = XMLRepr(Node(), "text & stuff")  # type: ignore[arg-type]
        out = repr_.__xml__()
        assert "text &amp; stuff" in out
        assert out.startswith("<Node")
        assert out.endswith("</Node>")

    def test_nested_children_indent(self):
        @xmlclass
        class Child:
            def __init__(self, name):
                self.name = name

            def __xml__attrs__(self):
                return {"name": self.name}

        @xmlclass
        class Parent:
            def __init__(self, children):
                self.children = children

            def __xml__attrs__(self):
                return {"children": self.children}

        out = Parent([Child("a"), Child("b")]).__xml__()
        assert "<Parent" in out
        assert "</Parent>" in out
        assert out.count("<Child") == 2
