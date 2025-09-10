from functools import wraps

import click

from ._factory import DecoratorCompositor

dump = DecoratorCompositor.from_list([
    click.option('--indent', default=4, help='Number of spaces to use for indentation.'),
    click.option('--ensure-ascii/--no-ensure-ascii', default=True, help='Whether to escape non-ASCII characters.'),
    click.option('--sort-keys/--no-sort-keys', default=False, help='Whether to sort the output of dictionaries by key.'),
    click.option('--separators', default=None, help='Item and key separators.'),
    click.option('--allow-nan/--no-allow-nan', default=True, help='Whether to allow NaN and Infinity values.')
])
