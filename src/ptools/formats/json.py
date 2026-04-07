"""Reusable Click option bundles for JSON dump-style commands.

Exposes :data:`dump`, a :class:`DecoratorCompositor` that adds the
standard set of ``json.dumps`` options (``--indent``, ``--sort-keys``,
``--ensure-ascii``, ``--separators``, ``--allow-nan``) to any Click
command.
"""
from functools import wraps

import click

from ..utils.decorator_compistor import DecoratorCompositor

__version__ = "0.1.0"

dump = DecoratorCompositor.from_list([
    click.option('--indent', default=4, help='Number of spaces to use for indentation.'),
    click.option('--ensure-ascii/--no-ensure-ascii', default=True, help='Whether to escape non-ASCII characters.'),
    click.option('--sort-keys/--no-sort-keys', default=False, help='Whether to sort the output of dictionaries by key.'),
    click.option('--separators', default=None, help='Item and key separators.'),
    click.option('--allow-nan/--no-allow-nan', default=True, help='Whether to allow NaN and Infinity values.')
])
