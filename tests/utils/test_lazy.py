"""Tests for ptools.utils.lazy.Lazy."""
from ptools.utils.lazy import Lazy


def test_not_evaluated_until_accessed():
    calls = []

    def factory():
        calls.append(1)
        return "hello"

    lazy = Lazy(factory)
    assert calls == []
    assert lazy.value == "hello"
    assert calls == [1]


def test_memoized():
    calls = []

    def factory():
        calls.append(1)
        return object()

    lazy = Lazy(factory)
    first = lazy.value
    second = lazy.value
    assert first is second
    assert calls == [1]


def test_value_may_be_none():
    lazy = Lazy(lambda: None)
    assert lazy.value is None
