import sys

from ptools.utils.print import fdebug
from ptools.lib.flow.utils import stream, yield_scope, read_stream

class FlowRunner:
    def __init__(self, globals=None):
        self.globals = globals if globals is not None else {}

    def run(self, expression: str, debug=False, vars={}):
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
            
        while not eval(condition, self.globals, local_scope):
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
