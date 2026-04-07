"""Decorators that declare the external things a command needs.

Each decorator in this module serves two purposes:

1. At call time, it validates that the required library, binary, or
   API key is actually available and raises (or prompts) otherwise.
2. At decoration time, it *announces* the requirement into a
   module-level registry so tooling can enumerate everything ptools
   depends on without running any commands. See
   :func:`announced_requirements` and
   ``scripts/generate_requirements.py``.
"""

import click
from dataclasses import dataclass, field
from functools import wraps
from typing import List, Dict, Callable, Tuple, Union

from ptools.utils.enums import LogicalOperators
from ptools.utils.protocols import ImplementsGet


@dataclass(frozen=True)
class LibraryRequirement:
    """A Python library that must be importable."""

    module: str
    pypi_name: str | None = None
    prompt_install: bool = False

    @property
    def pip_name(self) -> str:
        """Name to pass to ``pip install`` (defaults to :attr:`module`)."""
        return self.pypi_name or self.module


@dataclass(frozen=True)
class BinaryRequirement:
    """One or more executables that must be on ``$PATH``."""

    names: Tuple[str, ...]
    logical_operator: str  # 'and' | 'or'


@dataclass(frozen=True)
class KeyRequirement:
    """An API key / secret that must be resolvable from some store."""

    name: str
    aliases: Tuple[str, ...]
    logical_operator: str  # 'and' | 'or'


Requirement = Union[LibraryRequirement, BinaryRequirement, KeyRequirement]

_REQUIREMENTS: list[Requirement] = []


def announce(requirement: Requirement) -> None:
    """Record a requirement in the module-level registry.

    This is called by every :mod:`ptools.utils.require` decorator at
    decoration time (i.e. when the surrounding module is imported), so
    simply importing a module is enough to make its requirements
    discoverable without actually invoking its commands.
    """
    _REQUIREMENTS.append(requirement)


def announced_requirements() -> list[Requirement]:
    """Return a snapshot of every requirement announced so far.

    Callers should import the modules they care about (or walk the
    whole :mod:`ptools` package) before reading the registry — a
    requirement only appears here once the module that uses the
    corresponding decorator has been imported.
    """
    return list(_REQUIREMENTS)


def clear_announcements() -> None:
    """Empty the requirement registry. Primarily useful in tests."""
    _REQUIREMENTS.clear()


def _require_library(library: str):
    "Ensure that a library is installed."
    import importlib.util
    if importlib.util.find_spec(library) is None:
        raise ImportError(f"{library} is not installed.")

def _require_binary(binary: str):
    "Ensure that a binary is available in the system PATH."
    import shutil
    if shutil.which(binary) is None:
        raise ImportError(f"Binary '{binary}' is not found in PATH.")

def _require_key(
    requirements: Dict[str, List[str] | str],
    stores: List[ImplementsGet],
    logical_operator: LogicalOperators = LogicalOperators.OR):
    """Given a dictionary of required keys and a list of possible key names,
    ensure that at least one is set in some store and apply the logical operator to the results."""

    requirements = { k : (v if isinstance(v, list) else [v]) for k, v in requirements.items() }
    results = {}
    logical_results = []

    def get_value_from_stores(key_name: str):
        for store in stores:
            value = store.get(key_name)
            if value is not None:
                return value
        return None

    def find_first_value(key_names: List[str] | str):
        key_names = key_names if isinstance(key_names, list) else [key_names]
        for name in key_names:
            value = get_value_from_stores(name)
            if value is not None:
                return value
        return None

    for key, names in requirements.items():
        value = find_first_value(names)
        results[key] = value
        logical_results.append(value is not None)

    logical_operator.ensure(
        logical_results,
        f"Some or all keys missing: {', '.join([k for k, v in results.items() if v is None])}"
    )

    return results

# Decorators
def library(library: str, pypi_name: str | None= None, prompt_install: bool = False):
    "Click decorator to ensure a library is installed."
    announce(LibraryRequirement(
        module=library,
        pypi_name=pypi_name,
        prompt_install=prompt_install,
    ))
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                _require_library(library)
            except ImportError as e:
                if prompt_install:
                    click.echo(f"{library} is not installed. Please install it to use this feature.")
                    import sys
                    if click.confirm(f"Do you want to install {library} now?"):
                        import subprocess
                        subprocess.check_call([sys.executable, "-m", "pip", "install", pypi_name or library])
                        click.echo(f"{library} has been installed. Please restart the command.")
                        sys.exit(0)
                    else:
                        click.echo("Operation cancelled.")
                        sys.exit(1)
                else:
                    raise e
            return f(*args, **kwargs)
        return wrapper
    return decorator

def binary(names: List[str] | str, logical_operator: LogicalOperators = LogicalOperators.AND, key: str | None = None):
    "Click decorator to ensure a binary is available."
    _names = tuple(names) if isinstance(names, list) else (names,)
    announce(BinaryRequirement(
        names=_names,
        logical_operator=logical_operator.value,
    ))
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            binaries = names if isinstance(names, list) else [names]
            binaries_found = []
            for binary in binaries:
                try:
                    _require_binary(binary)
                    binaries_found.append(binary)
                except ImportError:
                    if logical_operator == LogicalOperators.AND:
                        raise
            if logical_operator == LogicalOperators.OR and not binaries_found:
                raise ImportError(f"None of the specified binaries were found: {', '.join(binaries)}")

            if key:
                kwargs[key] = binaries_found

            return f(*args, **kwargs)
        return wrapper
    return decorator

def key(
    names: Dict[str, List[str] | str],
    stores: List[ImplementsGet],
    logical_operator: LogicalOperators = LogicalOperators.OR,
):
    "Click decorator to ensure that at least one of the possible API key names is set in the store."
    for _key_name, _aliases in names.items():
        _alias_tuple = tuple(_aliases) if isinstance(_aliases, list) else (_aliases,)
        announce(KeyRequirement(
            name=_key_name,
            aliases=_alias_tuple,
            logical_operator=logical_operator.value,
        ))
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            value = _require_key(names, stores, logical_operator)
            for k, v in value.items():
                kwargs[k] = v
            return f(*args, **kwargs)
        return wrapper
    return decorator