from functools import wraps 
import click
from ptools.utils.decorator_compistor import DecoratorCompositor
from .values import OutputFlavorKind
from .parenthesizer import Parenthesizer

output_flavor = DecoratorCompositor.from_list([
    click.option('--flavor', '-fv', type=click.Choice(OutputFlavorKind), default=OutputFlavorKind.plain, help='Output format flavor.'),
])
    
debug_scope = DecoratorCompositor.from_list([
    click.option('--debug/--no-debug', default=False, help='Print scope information.'),
])
        

# Parse Expression Decorator
def parse_expression(expression_args, exec_flag, economic_flag, default='x'):
    expression = ' '.join(expression_args) or default
    if exec_flag:
        expression = f'exec(f"""{expression}""")'
    if economic_flag:
        tree = Parenthesizer.parser.parse(expression)
        rf = Parenthesizer.SugarToParen()
        expression = rf.transform(tree)
    return expression

def parse_flow_expression(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        expression_args = kwargs.pop('expression', [])
        exec_flag = kwargs.pop('exec', False)
        economic_flag = kwargs.pop('economic', False)
        expression = parse_expression(expression_args, exec_flag, economic_flag)
        kwargs['expression'] = expression
        return func(*args, **kwargs)
    return wrapper

flow_expression = DecoratorCompositor.from_list([
    click.argument('expression', type=str, required=True, nargs=-1),
    click.option('--exec', '-e', is_flag=True, default=False, help='Execute fstring as a shell command.'),
    click.option('--economic', '-E', is_flag=True, default=False, help='Use economic syntax (no parentheses).'),
    parse_flow_expression
])
