import click
from ptools.utils.decorator_compistor import DecoratorCompositor

workspace_command = DecoratorCompositor.from_list([
    click.option('--max-workers', '-j', default=4, help='Maximum number of concurrent workers.', type=int),
    click.option('--query', '-q', default=None, help='Filter projects by name containing this string.', type=str),
    click.option('--regex', '-g', is_flag=True, help='Interpret the query as a regular expression.')
])