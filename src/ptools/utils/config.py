import os
import json
import click

from ptools.utils.print import FormatUtils

class ConfigFile():
    def __init__(self, name, path="~/.ptools", quiet=False):
        self.name = name
        self.path = os.path.expanduser(path)
        self.file_path = os.path.join(self.path, f"{self.name}.json")
        self.data = {}
        self.quiet = quiet

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                try:
                    self.data = json.load(f)
                except json.JSONDecodeError:
                    msg = f"Error reading config file {self.file_path}. File may be corrupted."
                    self._echo(FormatUtils.error(msg))
                    raise ValueError(msg)
                except Exception as e:
                    msg = f"Unexpected error reading config file {self.file_path}: {str(e)}"
                    self._echo(FormatUtils.error(msg))
                    raise e
        else:
            with open(self.file_path, 'w') as f:
                json.dump(self.data, f, indent=4)
                self._echo(FormatUtils.info(f"Created new config file at {self.file_path}"))
        
        self._echo(FormatUtils.success(f"Loaded config file {self.file_path}"))

    def _echo(self, *args, **kwargs):
        if not self.quiet:
            click.echo(*args, **kwargs)

    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def set(self, key, value):
        self.data[key] = value
        with open(self.file_path, 'w') as f:
            json.dump(self.data, f, indent=4)
        self._echo(FormatUtils.success(f"Updated config file {self.file_path} with key '{key}'"))
        return self.data[key]
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
            with open(self.file_path, 'w') as f:
                json.dump(self.data, f, indent=4)
            self._echo(FormatUtils.success(f"Deleted key '{key}' from config file {self.file_path}"))
        else:
            self._echo(FormatUtils.warning(f"Key '{key}' not found in config file {self.file_path}"))
        return self.data
    
    def list(self):
        if not self.data:
            self._echo(FormatUtils.warning(f"No data found in config file {self.file_path}"))
            return {}
        self._echo(FormatUtils.info(f"Listing contents of config file {self.file_path}:"))
        for key, value in self.data.items():
            self._echo(f"{key}: {value}")
        return self.data
    
    def clear(self):
        self.data = {}
        with open(self.file_path, 'w') as f:
            json.dump(self.data, f, indent=4)
        self._echo(FormatUtils.success(f"Cleared all data from config file {self.file_path}"))
        return self.data
    
    def upsert(self, key, value):
        if key in self.data:
            self._echo(FormatUtils.info(f"Updating existing key '{key}' in config file {self.file_path}"))
        else:
            self._echo(FormatUtils.info(f"Adding new key '{key}' to config file {self.file_path}"))
        return self.set(key, value)
    
    def exists(self, key):
        exists = key in self.data
        if exists:
            self._echo(FormatUtils.success(f"Key '{key}' exists in config file {self.file_path}"))
        else:
            self._echo(FormatUtils.warning(f"Key '{key}' does not exist in config file {self.file_path}"))
        return exists
    
    def __repr__(self):
        return f"<ConfigFile(name={self.name}, path={self.path})>"
    
    def __str__(self):
        return f"ConfigFile(name={self.name}, path={self.path}, data={self.data})"
    
    def __getitem__(self, key):
        return self.get(key)
    
    def __setitem__(self, key, value):
        return self.set(key, value)
    
    def __delitem__(self, key):
        return self.delete(key)
    
    def __contains__(self, key):
        return self.exists(key)
    
    def __iter__(self):
        return iter(self.data.items())
    
    def __len__(self):
        return len(self.data)
    
    def __getattr__(self, item):
        if item in self.data:
            return self.data[item]
        raise AttributeError(f"'ConfigFile' object has no attribute '{item}'")
    
    def __setattr__(self, key, value):
        if key in ['name', 'path', 'file_path', 'data', 'quiet']:
            super().__setattr__(key, value)
        else:
            self.set(key, value)
    
    def __delattr__(self, item):
        if item in ['name', 'path', 'file_path', 'data', 'quiet']:
            super().__delattr__(item)
        else:
            self.delete(item)

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], str):
            return self.get(args[0])
        elif len(args) == 2:
            return self.set(args[0], args[1])
        else:
            raise TypeError("ConfigFile can be called with either one string argument (key) or two arguments (key, value).")
        
        return self