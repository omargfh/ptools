import click
from functools import wraps

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

def binary(binary):
    "Click decorator to ensure a binary is available."
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            _require_binary(binary)
            return f(*args, **kwargs)
        return wrapper
    return decorator
