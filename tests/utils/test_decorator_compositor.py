"""Tests for ptools.utils.decorator_compistor.DecoratorCompositor."""
from ptools.utils.decorator_compistor import DecoratorCompositor


def _wrap(name: str):
    """Return a decorator that appends `name` to the function's .trace list."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            return result + [name]
        wrapper.trace = getattr(fn, "trace", []) + [name]  # type: ignore
        return wrapper
    return decorator


def test_apply_order_is_outer_to_inner():
    # Decorators are applied in reverse of list order, so the first entry in the
    # list is the outermost wrapper - just like stacking @a then @b in source.
    comp = DecoratorCompositor.from_list([_wrap("a"), _wrap("b"), _wrap("c")])

    @comp.decorate()
    def base():
        return []

    # Innermost runs first: c, then b, then a.
    assert base() == ["c", "b", "a"]


def test_add_extends_existing_compositor():
    comp = DecoratorCompositor()
    comp.add(_wrap("only"))

    @comp.decorate()
    def base():
        return []

    assert base() == ["only"]


def test_empty_compositor_is_identity():
    comp = DecoratorCompositor()

    @comp.decorate()
    def base():
        return "unchanged"

    assert base() == "unchanged"
