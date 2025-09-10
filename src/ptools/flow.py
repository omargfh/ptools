import click

from ptools.lib.flow.values import StreamValue, OutputValue
from ptools.lib.flow.runner import FlowRunner
from ptools.lib.flow.decorators import output_flavor, debug_scope
from ptools.lib.flow.utils import read_stream, stream, yield_scope, create_global_scope
from ptools.utils.print import fdebug 

globals = create_global_scope()
Runner = FlowRunner(globals=globals)

@click.group()
def cli():
    """Pythonic FP-flavored workflow engine."""
    pass

@click.command()
def read():
    """Development command to read from stdin and print the StreamValue representation."""
    for flow_value in stream():
        click.echo(f"{flow_value} (type: {type(flow_value.value).__name__})")
        
@click.command()
@click.argument('expression')
@debug_scope.decorate()
@output_flavor.decorate()
def map(expression, flavor, debug):
    """Apply a Python expression to each streamed input line."""
    output = OutputValue(flavor=flavor)
    results = []
    for result, _ in Runner.run(expression, debug=debug):
        results.append(result)
    click.echo(output.format(results))
            
@click.command()
@click.argument('start', type=int)
@click.argument('end', type=int)
@click.argument('step', type=int, default=1, required=False)
@output_flavor.decorate()
def frange(start, end, step, flavor):
    """Generate a range of numbers from start to end-1, where start, end, and step are read from stdin."""
    output = OutputValue(flavor=flavor)
    result = list(range(start, end, step))
    click.echo(output.format(result))
        
@click.command()
@click.argument('expression')
@debug_scope.decorate()
@output_flavor.decorate()
def filter(expression, flavor, debug):
    """Filter streamed input lines based on a Python expression."""
    output = OutputValue(flavor=flavor)
    results = []
    for result, fv in Runner.run(expression, debug=debug):
        if result:
            results.append(fv.value)
    click.echo(output.format(results))

@click.command()
@click.argument('expression')
@click.option('--accumulator', '-a', default=None, help='Initial value for the accumulator.')
@debug_scope.decorate()
@output_flavor.decorate()
def reduce(expression, accumulator, flavor, debug):
    """Reduce streamed input lines based on a Python expression."""
    accumulator = StreamValue(accumulator).value if accumulator is not None else None
    output = OutputValue(flavor=flavor)
    
    for result, _ in \
        Runner.run(expression, debug=debug, vars={'acc': accumulator}):
        accumulator = result
    
    click.echo(f"{output.format(accumulator)}")
    
@click.command()
@click.argument('expression')
@output_flavor.decorate()
def exec(expression, flavor):
    """Execute a Python expression with access to the global scope."""
    try:
        result = eval(expression, globals)
        click.echo(f"{OutputValue(flavor=flavor).format(result)}")
    except Exception as e:
        click.echo(f"Error: {e}")
        
@click.command()
@click.argument('expression', required=False, default='x')
@debug_scope.decorate()
@output_flavor.decorate()
def unique(expression, flavor, debug):
    """Yield unique items from the stream based on a Python expression."""
    seen = set()
    output = OutputValue(flavor=flavor)
    results = []
    
    for result, fv in Runner.run(expression, debug=debug):
        key = result
        if key not in seen:
            seen.add(key)
            results.append(fv.value)
    
    click.echo(output.format(results))

@click.command()
@click.argument('expression', required=False, default='x')
@debug_scope.decorate()
@output_flavor.decorate()
def group(expression, flavor, debug):
    """Group items from the stream based on a Python expression."""
    from collections import defaultdict
    groups = defaultdict(list)
    
    for result, fv in Runner.run(expression, debug=debug):
        key = result
        groups[key].append(fv.value)
            
    click.echo(OutputValue(flavor=flavor).format(dict(groups)))
    
@click.command()
@click.argument('expression')
@debug_scope.decorate()
@output_flavor.decorate()
def foreach(expression, flavor, debug):
    """Foreach loop over items generated from each streamed input line."""
    output = OutputValue(flavor=flavor)

    for result, _ in Runner.run(expression, debug=debug):
        if result is not None \
            and not (isinstance(result, list) and len(result) == 0) \
            and not (isinstance(result, str) and result.strip() == ''):
            click.echo(f"{output.format(result)}")
            
@click.command()
@click.argument('expression')
@click.option('--initial', '-i', default=None, help='Initial value for the x variable.')
@click.option('--condition', '-c', default='True', help='Loop condition as a Python expression.')
@click.option('--update-on-none', is_flag=True, default=False, help='Continue updating x even if the expression returns None.')
@click.option('--output-last/--output-all', is_flag=True, default=True, help='Output only the final result after the loop ends.')
@output_flavor.decorate()
@debug_scope.decorate()
def while_loop(expression, initial, condition, update_on_none, flavor, debug, output_last):
    """While loop executing a Python expression as long as the condition is true."""
    output = OutputValue(flavor=flavor)
    
    for result, _, is_last in \
        Runner.run_while(expression,
                         initial=initial,
                         condition=condition,
                         update_on_none=update_on_none,
                         debug=debug):
        if not output_last or is_last:
            click.echo(f"{output.format(result)}")
    

cli.add_command(read, name='read')
cli.add_command(map, name='map')
cli.add_command(frange, name='range')
cli.add_command(filter, name='filter')
cli.add_command(reduce, name='reduce')
cli.add_command(unique, name='unique')
cli.add_command(group, name='group')
cli.add_command(exec, name='exec')
cli.add_command(foreach, name='foreach')
cli.add_command(while_loop, name='while')