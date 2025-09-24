import os
from pathlib import Path
import json
import click

from ptools.utils.print import FormatUtils
from ptools.utils.encrypt import Encryption, EncryptionError

class ConfigFile():
    def __init__(self, name, path="~/.ptools", quiet=False, encrypt=False):
        self.name = name
        self.path = os.path.expanduser(path)
        self.file_path = os.path.join(self.path, f"{self.name}.json")
        os.makedirs(Path(self.file_path).parent, exist_ok=True)
        self.data = {}
        self.quiet = quiet

        if encrypt:
            encryption_service_name = f"com.ptools.config.{self.name}"
            self.encryption = Encryption(service_name=encryption_service_name)
        else:
            self.encryption = None

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f: # r+ for possible write
                self.data = self._reads(f)
        else:
            with open(self.file_path, 'w') as f:
                self.data = {}
                self._writes(f, self.data)
                self._echo(FormatUtils.info(f"Created new config file at {self.file_path}"))

        self._echo(FormatUtils.success(f"Loaded config file {self.file_path}"))

    def _echo(self, *args, **kwargs):
        if not self.quiet:
            click.echo(*args, **kwargs)

    def _reads(self, f):
        try:
            content = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in config file {self.file_path}: {e}")
        except FileNotFoundError:
            raise RuntimeError(f"Config file {self.file_path} not found.")
        except PermissionError:
            raise RuntimeError(f"Permission denied when accessing config file {self.file_path}.")
        except Exception as e:
            raise RuntimeError(f"Failed to read config file {self.file_path}: {e}")

        if content.get('encrypted') is None and content.get('data') is None:
            """Backwards compatibility for old config files."""
            return content


        """There are 2 degrees of freedom here:
        1. Content encryption
        2. Encryption service availability

        A content can be encrypted if it wasn't before, but not the
        other way around.
        """
        if content.get('encrypted', False):         # Content is encrypted
            if not self.encryption:                 # But no encryption service is configured
                raise EncryptionError("Encryption is enabled but no encryption service is configured.")
            else:
                try:
                    # { encrypted: True, data: EncryptedString(jsonString) }
                    # Call decrypt on the data field to get the original JSON
                    # string then parse it as JSON
                    content = json.loads(self.encryption.decrypt(content.get('data')))
                except Exception as e:
                    raise EncryptionError(f"Failed to decrypt config file {self.file_path}: {e}")
        else:                         # Content is not encrypted
            content = content.get('data') if isinstance(content, dict) else content

        if not isinstance(content, dict):
            raise TypeError("Config file content must be a dictionary.")
        return content


    def _writes(self, f, data):
        """Write data to the config file."""
        if self.encryption:
            content = {
                'encrypted': True,
                'data': self.encryption.encrypt(json.dumps(data, indent=4))
            }
        else:
            content = {
                'encrypted': False,
                'data': data
            }

        if not isinstance(content, dict):
            raise TypeError("Data must be a dictionary.")
        if not self.quiet:
            self._echo(FormatUtils.info(f"Writing config file {self.file_path}..."))

        try:
            json.dump(content, f, indent=4)
        except Exception as e:
            raise RuntimeError(f"Failed to write config file {self.file_path}: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        with open(self.file_path, 'w') as f:
            self._writes(f, self.data)
        self._echo(FormatUtils.success(f"Updated config file {self.file_path} with key '{key}'"))
        return self.data[key]

    def delete(self, key):
        if key in self.data:
            del self.data[key]
            with open(self.file_path, 'w') as f:
                self._writes(f, self.data)
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
            self._writes(f, self.data)
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
    
    def replace(self, new_data):
        if not isinstance(new_data, dict):
            raise TypeError("New data must be a dictionary.")
        self.data = new_data
        with open(self.file_path, 'w') as f:
            self._writes(f, self.data)
        self._echo(FormatUtils.success(f"Replaced all data in config file {self.file_path}"))
        return self.data
    
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
        if key in ['name', 'path', 'file_path', 'data', 'quiet', 'encryption']:
            super().__setattr__(key, value)
        else:
            self.set(key, value)

    def __delattr__(self, item):
        if item in ['name', 'path', 'file_path', 'data', 'quiet', 'encryption']:
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
    
class KeyValueStore(ConfigFile):
    # This started as a simple key-value store for config purposes
    # but has evolved into a more general key-value store.
    # We offer an alias for semantic clarity.
    pass