import click
from functools import wraps
from enum import Enum
from typing import List

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

# Decorators
def library(library, prompt_install=False):
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
                        subprocess.check_call([sys.executable, "-m", "pip", "install", library])
                    else:
                        click.echo("Operation cancelled.")
                        return
                else:
                    raise e
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

class LogicalOperators(Enum):
    AND = 'and'
    OR = 'or'

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
