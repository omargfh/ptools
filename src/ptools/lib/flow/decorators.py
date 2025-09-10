import click
from ptools.utils.decorator_compistor import DecoratorCompositor

from .values import OutputFlavorKind

output_flavor = DecoratorCompositor.from_list([
    click.option('--flavor', type=click.Choice(OutputFlavorKind), default=OutputFlavorKind.plain, help='Output format flavor.'),
])
    
debug_scope = DecoratorCompositor.from_list([
    click.option('--debug/--no-debug', default=False, help='Enable debug mode to print scope information.'),
])
        
    