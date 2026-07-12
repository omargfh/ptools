import sys

from ptools.utils.print import fdebug
from ptools.lib.flow.utils import stream, yield_scope, read_stream

class FlowRunner:
    def __init__(self, globals=None):
        self.globals = globals if globals is not None else {}

    def run(self, expression: str, debug: bool=False, vars: dict={}, yield_scope=yield_scope, stream=stream):
        """Runs the given expression for each value in the stream,
        yielding the result along with the original flow value.

        :param expression: The expression to evaluate for each flow value. It has to be a valid Python expression
                            that can use the variables defined in the flow scope.
        :param debug: If True, prints debug information about the runtime scope and the expression being evaluated.
        :param vars: A dictionary of additional variables to include in the scope for the expression.
        :param yield_scope: A function that yields the scope for each flow value.
        :param stream: A function that returns an iterable of flow values.

        :yield: A list containing the result of the expression and the original flow value.
        """
        for flow_value in stream():
            try:
                for scope in yield_scope(flow_value):
                    if debug:
                        sys.stderr.write(fdebug(
                            "Runtime Debug Info",
                            expression=expression,
                            local_scope=scope) + "\n",
                        )
                    scope = {**scope, **vars}
                    result = eval(expression, self.globals, scope)
                    yield [result, flow_value]
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")

    def run_while(
        self,
        expression: str,
        initial: str = None,
        condition: str = 'True',
        update_on_none: bool = False,
        debug: bool = False
    ):
        piped_input = read_stream()
        local_scope = {'x': None, 'i': 0, 'stdin': piped_input}

        initial = eval(initial, self.globals, local_scope) if initial is not None else None
        if initial is not None:
            local_scope['x'] = initial

        while eval(condition, self.globals, local_scope):
            try:

                if debug:
                    sys.stderr.write(fdebug(
                        "Runtime Debug Info",
                        condition=condition,
                        expression=expression,
                        local_scope=local_scope) + "\n",
                    )

                result = eval(expression, self.globals, local_scope)
                yield [result, None, False]
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
                break

            local_scope['i'] += 1
            if result is not None or update_on_none:
                local_scope['x'] = result

        yield [local_scope['x'], None, True]
