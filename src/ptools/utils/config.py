"""Persistent, optionally-encrypted key/value config files for ptools.

Provides :class:`ConfigFile` and the lazy variant :class:`LazyConfigFile`
for storing user configuration on disk, plus :func:`config_to_CLI` to
expose CRUD operations as a Click command group.
"""
import os
from pathlib import Path
import click

from typing import Generic, TypeVar, overload
from pydantic import BaseModel

from ptools.utils.print import ASCIIEscapes, FormatUtils
from ptools.utils.encrypt import Encryption, EncryptionError
from ptools.utils.re import filter_dict_by_key

from .serial import  SerializerDeserializerFactory

__version__ = "0.1.0"

RESERVED_CONFIG_KEYS = [
    'name', 'path', 'file_path',
    'data', 'quiet', 'encryption',
    'ref', 'format', 'serial', 'model',
    '_validate', '_initialized'
]

T = TypeVar('T', bound=BaseModel)
class ConfigFile(Generic[T]):
    """A simple configuration file manager with optional keychain encryption.

    Config files are stored in a user-specified directory (defaulting to ``~/.ptools``) with a specified name and format
    (defaulting to JSON). Each config file can optionally be encrypted using a keychain service. It can also provide a
    validation model using Pydantic to ensure the config data adheres to a specific schema or default values.

    :param name: Name of the config file (without extension).
    :param path: Directory to store the config file. Defaults to ``~/.ptools``.
    :param quiet: If True, suppresses informational messages. Defaults to False.
    :param encrypt: If True, enables encryption for the config file. Defaults to False.
    :param format: Serialization format for the config file. Defaults to "json". Supported formats
                        are determined by the SerializerDeserializerFactory.
    :param model: Optional Pydantic model class for validating config data. If provided, all data will be validated
                        against this model on load and before saving. This ensures the config adheres to a specific
                        schema and can provide default values.

    Example::

        from ptools.utils.config import ConfigFile
        from pydantic import BaseModel, Field

        class MyConfigModel(BaseModel):
            api_key: str
            timeout: int = Field(default=30, description="Timeout in seconds")

        config = ConfigFile[MyConfigModel](name="my_config", encrypt=True, model=MyConfigModel)
        config.set("api_key", "my_secret_key")
        print(config.get("api_key"))

        timeout = config.typed.timeout  # Access with validation and defaults
        print(timeout)  # Will print 30 if not set, or the value if set

    See also :class:`~ptools.utils.config.LazyConfigFile` for a lazily-initialized version of this class.
    """
    def __init__(
        self,
        name,
        path="~/.ptools",
        quiet=False,
        encrypt=False,
        format="json",
        model: type[T] | None = None,
    ):
        self.serial = SerializerDeserializerFactory.get(format)
        self.name = name
        self.path = os.path.expanduser(path)
        self.file_path = os.path.join(self.path, f"{self.name}.{self.serial.ext}")
        os.makedirs(Path(self.file_path).parent, exist_ok=True)
        self.quiet = quiet
        self.model = model
        self.data  = self._validate({})

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
                self.data = self._validate({})
                self._writes(f, self.data)
                self._echo(FormatUtils.info(f"Created new config file at {self.file_path}"))

        self._echo(FormatUtils.success(f"Loaded config file {self.file_path}"))

    def _echo(self, *args, **kwargs):
        if not self.quiet:
            click.echo(*args, **kwargs)

    def _validate(self, data):
        if self.model is not None:
            try:
                return self.model.model_validate(data).model_dump()
            except Exception as e:
                raise ValueError(f"Config data does not match the expected model: {e}")
        return data

    def _reads(self, f):
        try:
            content = self.serial.load(f)
        except self.serial.DecodeError as e:
            raise ValueError(f"Invalid {self.serial.name} format in config file {self.file_path}: {e}")
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
                    # { encrypted: True, data: EncryptedString(serialString) }
                    # Call decrypt on the data field to get the original serialized
                    # string then parse it as the original data structure.
                    content = self.serial.loads(self.encryption.decrypt(content.get('data')))
                except Exception as e:
                    raise EncryptionError(f"Failed to decrypt config file {self.file_path}: {e}")
        else:                         # Content is not encrypted
            content = content.get('data') if isinstance(content, dict) else content

        if not isinstance(content, dict):
            raise TypeError("Config file content must be a dictionary.")

        return self._validate(content)

    def _writes(self, f, data):
        """Write data to the config file."""
        if self.encryption:
            content = {
                'encrypted': True,
                'data': self.encryption.encrypt(self.serial.dumps(data))
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
            self.serial.dump(content, f)
        except Exception as e:
            raise RuntimeError(f"Failed to write config file {self.file_path}: {e}")


    def get(self, key, default=None):
        """Return the stored value for ``key`` or ``default`` if missing."""
        return self.data.get(key, default)

    def set(self, key, value):
        """Persist ``value`` under ``key`` and write the file to disk."""
        self.data[key] = value
        with open(self.file_path, 'w') as f:
            self._writes(f, self.data)
        self._echo(FormatUtils.success(f"Updated config file {self.file_path} with key '{key}'"))
        return self.data[key]

    def delete(self, key):
        """Remove ``key`` from the config and rewrite the file. No-op if absent."""
        if key in self.data:
            del self.data[key]
            with open(self.file_path, 'w') as f:
                self._writes(f, self.data)
            self._echo(FormatUtils.success(f"Deleted key '{key}' from config file {self.file_path}"))
        else:
            self._echo(FormatUtils.warning(f"Key '{key}' not found in config file {self.file_path}"))
        return self.data

    @property
    def typed(self) -> T:
        """Return the config data validated as a Pydantic model instance.

        :raises ValueError: if no ``model`` was provided at construction.
        """
        if self.model is None:
            raise ValueError("No model defined for this ConfigFile instance.")
        return self.model.model_validate(self.data)

    def list(self):
        """Echo every stored key/value pair and return the underlying dict."""
        if not self.data:
            self._echo(FormatUtils.warning(f"No data found in config file {self.file_path}"))
            return {}
        self._echo(FormatUtils.info(f"Listing contents of config file {self.file_path}:"))
        for key, value in self.data.items():
            self._echo(f"{key}: {value}")
        return self.data

    def clear(self):
        """Wipe all stored data and rewrite the file."""
        self.data = {}
        with open(self.file_path, 'w') as f:
            self._writes(f, self.data)
        self._echo(FormatUtils.success(f"Cleared all data from config file {self.file_path}"))
        return self.data

    def upsert(self, key, value):
        """Insert or update ``key`` with ``value``, logging which case occurred."""
        if key in self.data:
            self._echo(FormatUtils.info(f"Updating existing key '{key}' in config file {self.file_path}"))
        else:
            self._echo(FormatUtils.info(f"Adding new key '{key}' to config file {self.file_path}"))
        return self.set(key, value)

    def exists(self, key):
        """Return whether ``key`` is stored in the config, with a status echo."""
        exists = key in self.data
        if exists:
            self._echo(FormatUtils.success(f"Key '{key}' exists in config file {self.file_path}"))
        else:
            self._echo(FormatUtils.warning(f"Key '{key}' does not exist in config file {self.file_path}"))
        return exists

    def replace(self, new_data):
        """Replace every entry with ``new_data`` and persist the result."""
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
        if item in RESERVED_CONFIG_KEYS:
            return super().__getattribute__(item)
        elif item in self.data:
            return self.data[item]
        raise AttributeError(f"'ConfigFile' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        if key in RESERVED_CONFIG_KEYS:
            super().__setattr__(key, value)
        else:
            self.set(key, value)

    def __delattr__(self, item):
        if item in RESERVED_CONFIG_KEYS:
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

    def close(self):
        """Close the underlying file handle if one is held open."""
        if self.ref and not self.ref.closed:
            self.ref.close()
            self._echo(FormatUtils.info(f"Closed config file {self.file_path}"))

class LazyConfigFile(ConfigFile[T]):
    """A lazily-initialized version of ConfigFile. The actual initialization is deferred until the first time an attribute is accessed.
    This can be useful for improving startup performance or avoiding unnecessary initialization when the config file may not be needed.
    """
    @overload
    def __init__(
        self,
        *args,
        model: type[T] = ...,
        **kwargs
    ) -> None: ...

    @overload
    def __init__(
        self,
        *args,
        model: None = None,
        **kwargs
    ) -> None: ...

    def __init__(self, *args, **kwargs):
        object.__setattr__(self, '_initialized', False)
        object.__setattr__(self, '_lazy_args', args)
        object.__setattr__(self, '_lazy_kwargs', kwargs)

    def _initialize(self):
        if not object.__getattribute__(self, '_initialized'):
            object.__setattr__(self, '_initialized', True)  # set BEFORE init to prevent re-entry
            args = object.__getattribute__(self, '_lazy_args')
            kwargs = object.__getattribute__(self, '_lazy_kwargs')
            super().__init__(*args, **kwargs)

    def __getattribute__(self, item):
        if item in ('_initialized', '_initialize', '_lazy_args', '_lazy_kwargs'):
            return object.__getattribute__(self, item)
        object.__getattribute__(self, '_initialize')()
        return super().__getattribute__(item)

    def __setattr__(self, key, value):
        if not object.__getattribute__(self, '_initialized'):
            # During init, use ConfigFile's normal __setattr__
            # which handles reserved vs data keys
            ConfigFile.__setattr__(self, key, value)
        else:
            super().__setattr__(key, value)

    def __getattr__(self, item):
        object.__getattribute__(self, '_initialize')()
        return super().__getattr__(item)

def config_to_CLI(
    config: ConfigFile | LazyConfigFile,
    cli: click.Group | None = None,
    name: str | None = None,
):
    """Create a CRUD command-line interface for a given ConfigFile or LazyConfigFile instance.
    The CLI will have commands to list, get, set, and delete key-value pairs in the config file.
    The CLI is built using Click and can be easily integrated into a larger command-line application.

    :param config: An instance of ConfigFile or LazyConfigFile to manage with the CLI.
    :param cli: An optional Click Group to which the config commands will be added. If
                    not provided, a new Click Group will be created.
    :param name: An optional name for the CLI group. If not provided, it will be derived from the config class name.

    Example::

        from ptools.utils.config import ConfigFile, config_to_CLI
        import click
        config = ConfigFile(name="my_config")
        cli = config_to_CLI(config)
        if __name__ == "__main__":
            cli()

    This will create a CLI with commands like:

    - ``python my_script.py config list``
    - ``python my_script.py config get <key>``
    - ``python my_script.py config set <key> <value>``
    - ``python my_script.py config delete <key>``
    """

    name = config.__class__.__name__\
        .removesuffix("File") \
        .removesuffix("Config") \
        .lower() if name is None else name

    @click.group(
        name=name,
        help=f"CLI for managing {config.__class__.__name__} instance at {config.file_path}."
    )
    def group():
        pass

    cli = cli or group


    def dump_one(key, value):
        if value is None:
            click.echo(f"{ASCIIEscapes.color(str(key), 'green')}: {ASCIIEscapes.color('None', 'red')}")
        else:
            click.echo(f"{ASCIIEscapes.color(str(key), 'green')}: {value}")

    @cli.command(name="list", help="List all key-value pairs in the config file.")
    @click.option('--query', '-q', help="Query to filter secrets")
    @click.option('--regex', '-g', is_flag=True, help="Use regex for filtering")
    def list(query: str | None = None, regex: bool = False):
        """List all key-value pairs in the config file."""
        data = filter_dict_by_key(config.list(), query, regex)

        # Empty State
        if not data or (isinstance(data, dict) and len(data) == 0):
            click.echo(FormatUtils.warning(f"No data found in config file {config.file_path}."))
            exit(1)

        # Table Output
        max_key_length = max(len(str(k)) for k in data.keys())
        for key, value in data.items():
            dump_one(str(key).ljust(max_key_length), value)

    @cli.command(name="get", help="Get the value of a key.")
    @click.argument('key')
    def get(key):
        """Get the value of a key."""
        value = config.get(key)
        if value is not None:
            click.echo(value)
        else:
            exit(1)

    @cli.command(name="set", help="Set the value of a key.")
    @click.argument('key')
    @click.argument('value')
    def set(key, value):
        """Set the value of a key."""
        config.set(key, value)
        click.echo(f"Set '{key}' to '{value}'.")

    @cli.command(name="delete", help="Delete a key.")
    @click.argument('key')
    def delete(key):
        """Delete a key."""
        if key not in config:
            click.echo(FormatUtils.warning(f"Key '{key}' not found in config file {config.file_path}."))
            exit(1)
        config.delete(key)
        click.echo(f"Deleted key '{key}'.")

    return cli



class KeyValueStore(ConfigFile):
    """Semantic alias for :class:`ConfigFile` when used as a generic key/value store.

    This started as a config-only utility but has grown into a general
    key/value store; this alias exists purely for clearer call sites.
    """
    pass

class DummyKeyValueStore(ConfigFile):
    """No-op :class:`ConfigFile` stand-in for tests and dry-run code paths.

    Every method is a pass-through that ignores writes and returns
    empty/default values, so callers can swap it in without changing
    their interface.
    """
    def __init__(self, *args, **kwargs):
        pass

    def get(self, key, default=None):
        return default

    def set(self, key, value):
        return value

    def delete(self, key):
        return None

    def list(self):
        return {}

    def clear(self):
        return {}

    def upsert(self, key, value):
        return value

    def exists(self, key):
        return False

    def replace(self, new_data):
        return new_data

    def close(self):
        pass