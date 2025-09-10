from functools import wraps

import click

from ptools.utils import require

from ..utils.decorator_compistor import DecoratorCompositor

dump = DecoratorCompositor.from_list([
    require.library('yaml', pypi_name='PyYAML', prompt_install=True),
    click.option('--sort-keys/--no-sort-keys', default=False, help='Whether to sort the output of dictionaries by key.'),
    click.option('--default-style', default=None, type=click.Choice(['', '|', '>', '\'', '"']), help='Default style for YAML output.'),
    click.option('--default-flow-style/--no-default-flow-style', default=False, help='Whether to use the block style or the flow style for collections.'),
    click.option('--allow-unicode/--no-allow-unicode', default=True, help='Whether to allow non-ASCII characters in the output.'),
    click.option('--canonical/--no-canonical', default=False, help='Whether to use the canonical form of YAML.'),
    click.option('--indent', default=2, help='Number of spaces to use for indentation.'),
    click.option('--width', default=80, help='Preferred line width for the output.'),
    click.option('--line-break', default=None, type=click.Choice(['\n', '\r\n', '\r']), help='Line break character to use.'),
    click.option('--encoding', default='utf-8', help='File encoding to use.'),
    click.option('--explicit-start/--no-explicit-start', default=False, help='Whether to include the document start marker (---).'),
    click.option('--explicit-end/--no-explicit-end', default=False, help='Whether to include the document end marker (...).')
])