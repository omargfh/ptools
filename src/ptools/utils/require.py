import click
from functools import wraps
from typing import List, Dict, Callable

from ptools.utils.enums import LogicalOperators
from ptools.utils.protocols import ImplementsGet

# Methods
def _require_library(library):
    "Ensure that a library is installed."
    import importlib.util
    if importlib.util.find_spec(library) is None:
        raise ImportError(f"{library} is not installed.")
    
def _require_binary(binary):
    "Ensure that a binary is available in the system PATH."
    import shutil
    if shutil.which(binary) is None:
        raise ImportError(f"Binary '{binary}' is not found in PATH.")

def _require_key(
    requirements: Dict[str, List[str] | str],
    stores: List[ImplementsGet],
    logical_operator=LogicalOperators.OR):
    """Given a dictionary of required keys and a list of possible key names,
    ensure that at least one is set in some store and apply the logical operator to the results."""
    
    requirements = { k : (v if isinstance(v, list) else [v]) for k, v in requirements.items() }
    results = {}
    logical_results = []
    
    def get_value_from_stores(key_name):
        for store in stores:
            value = store.get(key_name)
            if value is not None:
                return value
        return None
    
    def find_first_value(key_names):
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
def library(library, pypi_name=None, prompt_install=False):
    "Click decorator to ensure a library is installed."
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                _require_library(library)
            except ImportError as e:
                if prompt_install:
                    click.echo(f"{library} is not installed. Please install it to use this feature.")
                    if click.confirm(f"Do you want to install {library} now?"):
                        import subprocess
                        import sys
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

def binary(names: List[str] | str, logical_operator=LogicalOperators.AND, key=None):
    "Click decorator to ensure a binary is available."
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
    logical_operator=LogicalOperators.OR,
):
    "Click decorator to ensure that at least one of the possible API key names is set in the store."
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            value = _require_key(names, stores, logical_operator)
            for k, v in value.items():
                kwargs[k] = v
            return f(*args, **kwargs)
        return wrapper
    return decorator