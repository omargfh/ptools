from __future__ import annotations
from dataclasses import field
from typing import List, Union, Callable
from xml.sax.saxutils import escape
from functools import wraps 

class XMLRepr:
    INDENT_STRING = "  "
    def __init__(self, myself, children: List = list(), **attrs: dict[str, Union[str, Callable[[], str]]]):
        self.myself = myself
        self.attrs = attrs
        self.children = children
        
    def __post_init__(self):
        for child in self.children:
            if not hasattr(child, "__xml__") or not callable(child.__xml__):
                raise TypeError(f"Child {child} must implement __xml__()")
        
    def __xml__(self, indent=0):
        tagName = self.myself.__class__.__name__
        indentStr = self.INDENT_STRING * indent
        attrsStr = self._build_attrs()
        if self.children == []:
            return f"{indentStr}<{tagName} {attrsStr} />"
        elif hasattr(self.children, "__xml__") and callable(self.children.__xml__):
            return f"{indentStr}<{tagName} {attrsStr}>\n{self.children.__xml__(indent=indent + 1)}\n{indentStr}</{tagName}>"
        else:
            childrenStr = "\n".join(child.__xml__(indent=indent + 1) for child in self.children)
            return f"{indentStr}<{tagName} {attrsStr}>\n{childrenStr}\n{indentStr}</{tagName}>"

    def _build_attrs(self):
        if not self.attrs:
            return ""
        parts = []
        for k, v in self.attrs.items():
            value = v() if callable(v) else v
            parts.append(f'{self._to_camel_case(k)}="{escape(str(value))}"')
        return " ".join(parts)
    
    @staticmethod
    def _to_camel_case(s: str) -> str:
        parts = s.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])
    
def xmlclass(cls):
    def __xml__(self, **inner_kwargs):
        attrs = cls.__xml__attrs__(self)
        children = attrs.pop('children', [])
        repr = XMLRepr(self, children, **attrs)
        return repr.__xml__(**inner_kwargs)
    def __repr__(self):
        return self.__xml__()
    cls.__repr__ = __repr__
    cls.__xml__ = __xml__
    return cls