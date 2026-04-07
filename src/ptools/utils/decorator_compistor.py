"""Compose multiple decorators into a single, reusable decorator."""

__version__ = "0.1.0"


class DecoratorCompositor:
    """Stack of decorators that can be applied to a target function in order.

    The compositor lets callers build up a list of decorators dynamically
    (e.g. depending on runtime configuration) and then apply them all at
    once. Decorators are applied in reverse insertion order so that the
    first one added is the outermost wrapper, matching the visual order
    of stacked ``@decorator`` syntax.
    """

    def __init__(self):
        self.decorators = []

    @staticmethod
    def from_list(decorator_list):
        """Build a :class:`DecoratorCompositor` pre-populated from ``decorator_list``."""
        stack = DecoratorCompositor()
        for dec in decorator_list:
            stack.add(dec)
        return stack

    def add(self, decorator):
        """Append ``decorator`` to the stack."""
        self.decorators.append(decorator)

    def apply(self, f):
        """Wrap ``f`` with every stacked decorator and return the result."""
        for dec in reversed(self.decorators):
            f = dec(f)
        return f

    def decorate(self):
        """Return a decorator that, when applied, calls :meth:`apply` on its target."""
        def decorator(f):
            return self.apply(f)
        return decorator
    