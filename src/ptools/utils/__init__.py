"""Reusable helpers shared across :mod:`ptools` subcommands.

This package collects small, self-contained utilities that several
CLI modules depend on - configuration file handling
(:mod:`~ptools.utils.config`), caching (:mod:`~ptools.utils.cache`),
lazy values (:mod:`~ptools.utils.lazy`), terminal formatting
(:mod:`~ptools.utils.print`), string case conversion
(:mod:`~ptools.utils.cases`), optional-dependency guards
(:mod:`~ptools.utils.require`), keyring-backed encryption
(:mod:`~ptools.utils.encrypt`), and more.
"""

__version__ = "0.1.0"


def flatten(lst):
    """Flatten one level of nesting from an iterable of iterables.

    :param lst: An iterable whose elements are themselves iterables.
    :returns: A flat :class:`list` containing every item from every
        inner iterable, preserving order.
    """
    return [item for sublist in lst for item in sublist]
