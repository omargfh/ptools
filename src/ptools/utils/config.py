"""Persistent, optionally-encrypted key/value config files for ptools.

Provides :class:`ConfigFile` and the lazy variant :class:`LazyConfigFile`
for storing user configuration on disk, plus :func:`config_to_CLI` to
expose CRUD operations as a Click command group.
"""
import os
import shutil
import sys
from pathlib import Path
import click

from typing import Generic, TypeVar, overload
from pydantic import BaseModel, TypeAdapter

from ptools.utils.print import ASCIIEscapes, FormatUtils
from ptools.utils.encrypt import Encryption, EncryptionError
from ptools.utils.re import filter_dict_by_key

from .serial import  SerializerDeserializerFactory

__version__ = "0.1.2"

RESERVED_CONFIG_KEYS = [
    'name', 'path', 'file_path',
    'data', 'quiet', 'encryption',
    'ref', 'format', 'serial', 'model',
    '_validate', '_initialized'
]


def starter_file(filename: str):
    """Return the packaged starter config matching *filename*, if any.

    ptools ships starter configs (e.g. the touch template library) in
    ``ptools/starters``; a missing user config is seeded from these so
    commands work out of the box. Returns an ``importlib.resources``
    traversable or ``None``.
    """
    try:
        from importlib.resources import files
        candidate = files("ptools") / "starters" / filename
        return candidate if candidate.is_file() else None
    except Exception:
        return None

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

        starter = None
        if not os.path.exists(self.file_path):
            starter = starter_file(f"{self.name}.{self.serial.ext}")

        if starter is not None:
            # Seed the user's config from the packaged starter, byte for
            # byte (preserves YAML comments), then load it normally.
            with open(self.file_path, 'wb') as f:
                f.write(starter.read_bytes())
            self._echo(FormatUtils.info(f"Seeded new config file at {self.file_path} from the packaged starter."))

        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f: # r+ for possible write
                self.data = self._reads(f)
        else:
            self.data = self._validate({})
            self._atomic_write(lambda f: self._writes(f, self.data))
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

    def _atomic_write(self, write_fn):
        """Run ``write_fn(file_object)`` against a temp file, then atomically
        replace ``self.file_path`` with it via :func:`os.replace`.

        ``write_fn`` does the actual serialization/encryption, so all of
        that work - including anything that can fail, like a keyring
        round-trip or an unserializable value - happens inside the temp
        file's write window instead of after the real target has already
        been truncated. If ``write_fn`` raises, the temp file is removed
        and ``self.file_path`` is left byte-for-byte as it was.

        The temp file is created next to ``self.file_path`` (same
        directory), not in the system temp dir, so :func:`os.replace`
        stays on one filesystem and stays atomic.
        """
        tmp_path = f"{self.file_path}.tmp"
        try:
            with open(tmp_path, 'w') as f:
                write_fn(f)
            if os.path.exists(self.file_path):
                # Carry over the existing file's permissions rather than
                # letting the freshly-created temp file's umask-derived
                # mode silently replace them.
                shutil.copymode(self.file_path, tmp_path)
            os.replace(tmp_path, self.file_path)
        except BaseException:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise

    def get(self, key, default=None):
        """Return the stored value for ``key`` or ``default`` if missing."""
        return self.data.get(key, default)

    def set(self, key, value):
        """Persist ``value`` under ``key`` and write the file to disk."""
        self.data[key] = value
        self._atomic_write(lambda f: self._writes(f, self.data))
        self._echo(FormatUtils.success(f"Updated config file {self.file_path} with key '{key}'"))
        return self.data[key]

    def delete(self, key):
        """Remove ``key`` from the config and rewrite the file. No-op if absent."""
        if key in self.data:
            del self.data[key]
            self._atomic_write(lambda f: self._writes(f, self.data))
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
        self._atomic_write(lambda f: self._writes(f, self.data))
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
        self._atomic_write(lambda f: self._writes(f, self.data))
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
        # Dunder lookups (__class__, __module__, ...) are exempt: they
        # resolve on the class itself and don't need real data, and
        # forcing init here would defeat laziness entirely. isinstance()
        # falls back to an explicit getattr(obj, '__class__') when the
        # fast type check misses (e.g. inspect.ismodule / inspect.isclass
        # probing every attribute of a module, as sphinx-autodoc does),
        # so without this exemption merely introspecting an uninitialized
        # instance's type would trigger a full init.
        if item in ('_initialized', '_initialize', '_lazy_args', '_lazy_kwargs') or (
            item.startswith('__') and item.endswith('__')
        ):
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
        # Mirrors the __getattribute__ exemption: a dunder that isn't
        # resolvable on the class doesn't exist, lazily or otherwise.
        if item.startswith('__') and item.endswith('__'):
            raise AttributeError(item)
        object.__getattribute__(self, '_initialize')()
        return super().__getattr__(item)

    def __repr__(self):
        # repr()/str() are implicit dunder calls (bypass __getattribute__
        # for the method lookup itself, per the exemption above), but their
        # inherited ConfigFile bodies read self.name/self.path/self.data,
        # which *are* real data and would still force a full init. Tools
        # routinely repr() arbitrary objects for debug logging (e.g.
        # Sphinx's event dispatcher does this for every emitted event), so
        # an uninitialized instance needs a safe answer that doesn't touch
        # the backing file or keyring.
        if object.__getattribute__(self, '_initialized'):
            return super().__repr__()
        args = object.__getattribute__(self, '_lazy_args')
        kwargs = object.__getattribute__(self, '_lazy_kwargs')
        name = kwargs.get('name', args[0] if args else None)
        return f"<{type(self).__name__}(name={name!r}, uninitialized)>"

    def __str__(self):
        if object.__getattribute__(self, '_initialized'):
            return super().__str__()
        return repr(self)

# Sentinel option value for "define a key that isn't stored yet". A NUL
# byte can't appear in a real key parsed out of JSON/YAML, so this can
# never collide with an actual entry.
_NEW_KEY = "\x00new-key"

# Value previews are descriptions on a single picker row; longer values
# are elided rather than wrapping the row.
_PREVIEW_MAX = 48


def _picker_output():
    """Build a prompt_toolkit output that renders to a real terminal.

    ``get`` is meant to be used as ``$(ptools settings get KEY)``, so its
    stdout may be a pipe. Same reasoning as ``ptools projects chdir``
    (``src/ptools/projects.py``): ``always_prefer_tty=True`` keeps the
    picker's UI on the terminal instead of letting it write into the pipe
    the caller is capturing a value from.
    """
    from prompt_toolkit.output.defaults import create_output

    return create_output(always_prefer_tty=True)


def _preview(value, masked=False):
    """Render *value* as a one-line picker description."""
    if masked:
        return "hidden" if value is not None else "unset"
    if value is None:
        return "unset"
    # Collapse whitespace so a multi-line value stays on its own row.
    text = " ".join(str(value).split())
    if len(text) > _PREVIEW_MAX:
        return f"{text[:_PREVIEW_MAX - 1]}…"
    return text


def _key_options(config, include_unset=False, allow_new=False):
    """Build ``(value, label, description)`` picker rows for *config*'s keys.

    Stored keys are described by a preview of their value — masked when
    the config is encrypted, since those values are secrets that
    shouldn't be painted onto the terminal just to browse key names.
    With *include_unset*, a model-backed config also offers the fields it
    declares but hasn't stored yet, described by their Pydantic
    ``Field(description=...)``.

    *allow_new* is honoured only for a config with no model. A model
    validates on every read and drops keys it doesn't declare, so an
    invented key would report success and then silently vanish; the
    model's own fields (via *include_unset*) are already the complete set
    of keys worth offering there.
    """
    masked = config.encryption is not None
    data = config.data
    options = [(str(key), str(key), _preview(value, masked)) for key, value in data.items()]

    if include_unset and config.model is not None:
        options += [
            (field_name, field_name, field.description or "unset")
            for field_name, field in config.model.model_fields.items()
            if field_name not in data
        ]

    if allow_new and config.model is None:
        options.append((_NEW_KEY, "+ new key", "define a key that isn't listed"))

    return options


def _field_annotation(config, key):
    """Return the type *key* is declared as, or ``None`` if undeclared."""
    model = config.model
    if model is None or key not in model.model_fields:
        return None
    return model.model_fields[key].annotation


def _coerce(config, key, value):
    """Validate *key*/*value* against the config's model before storing them.

    A model-backed config declares types (``PTOOLS_DEBUG: bool``) but the
    CLI hands over raw strings, and a model validates on every read. Two
    ways that goes wrong without a check here:

    - An unparseable value is written straight to disk and bricks the
      config: every later read raises in :meth:`ConfigFile._validate`,
      taking down *every* command for that config — including the
      ``delete`` that would undo it, and, for ``ptools settings``, every
      module that imports it.
    - A key the model doesn't declare is dropped on the next read, so the
      write reports success and then silently vanishes.

    Both become upfront usage errors, and values are stored with their
    declared type (``True``, not ``"true"``). A config with no model is a
    free-form key/value store and passes through untouched.

    Only the one field is validated, not the whole model: a config whose
    *other* fields are missing or stale shouldn't make an unrelated key
    unsettable.
    """
    model = config.model
    if model is None:
        return value

    if key not in model.model_fields:
        valid = ", ".join(sorted(model.model_fields))
        raise click.UsageError(
            f"'{key}' is not a valid key for this config. Valid keys: {valid}."
        )

    try:
        return TypeAdapter(model.model_fields[key].annotation).validate_python(value)
    except Exception as e:
        raise click.UsageError(f"Invalid value for '{key}': {e}") from e


def config_to_CLI(
    config: ConfigFile | LazyConfigFile,
    cli: click.Group | None = None,
    name: str | None = None,
):
    """Create a CRUD command-line interface for a given ConfigFile or LazyConfigFile instance.
    The CLI will have commands to list, get, set, delete, and interactively edit key-value pairs
    in the config file.
    The CLI is built using Click and can be easily integrated into a larger command-line application.

    ``get``, ``set``, and ``delete`` take their key as an optional
    argument: omit it and they open the same vite-style picker used by
    ``ptools projects chdir`` (:class:`~ptools.lib.tui.select.SelectApp`),
    listing each key alongside a preview of its value. ``edit`` is the
    fully interactive form — a browse/mutate loop that re-shows the
    picker after every change. Values are masked in the picker when the
    config is encrypted, and every prompt degrades to a plain usage error
    when stdin isn't a terminal, so scripted use is unaffected.

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
        help=f"CLI for managing {name}."
    )
    def group():
        pass

    cli = cli or group


    def dump_one(key, value):
        if value is None:
            click.echo(f"{ASCIIEscapes.color(str(key), 'green')}: {ASCIIEscapes.color('None', 'red')}")
        else:
            click.echo(f"{ASCIIEscapes.color(str(key), 'green')}: {value}")

    def require_tty(message):
        """Abort with *message* when there's no terminal to prompt on.

        Without this, omitting an argument in a non-interactive context
        (CI, a script with redirected stdin) surfaces as a prompt_toolkit
        traceback rather than a usage error.
        """
        if not sys.stdin.isatty():
            raise click.UsageError(message)

    def select(options, message, output=None, selected=None):
        """Run the shared vite-style picker; return ``None`` when cancelled."""
        from ptools.lib.tui.select import SelectApp

        return SelectApp(
            options, message=message, output=output, selected=selected
        ).run() or None

    def pick_key(message, output, include_unset=False, allow_new=False):
        """Pick a config key interactively, resolving the "+ new key" row.

        Returns ``None`` when the user cancels or the config is empty and
        there's nothing to offer.
        """
        from ptools.lib.tui.select import ask_text

        require_tty("KEY is required when not running interactively.")
        options = _key_options(config, include_unset=include_unset, allow_new=allow_new)
        if not options:
            click.echo(
                FormatUtils.warning(f"No keys stored in config file {config.file_path}."),
                err=True,
            )
            return None

        key = select(options, message, output=output)
        if key == _NEW_KEY:
            return ask_text("New key:", placeholder="KEY_NAME", output=output).strip() or None
        return key

    def ask_value(key, output):
        """Prompt for *key*'s value, seeded with what's stored today.

        A key the model declares as ``bool`` has exactly two valid
        answers, so it gets a picker rather than a free-text box the user
        could fail to satisfy. The rows carry the *strings* ``"true"`` and
        ``"false"``: returning a real ``False`` would be indistinguishable
        from :func:`select`'s falsy "cancelled" result. Callers run the
        answer through :func:`_coerce`, which turns it into a real bool.

        An encrypted config is prompted blank/unselected: seeding would
        show the stored secret. An empty submission cancels, matching the
        ``proc`` wizard's convention.
        """
        from ptools.lib.tui.select import ask_text

        require_tty("VALUE is required when not running interactively.")
        current = config.get(key)
        hide_current = config.encryption is not None

        if _field_annotation(config, key) is bool:
            preselected = None
            if current is not None and not hide_current:
                preselected = "true" if current else "false"
            return select(
                [("true", "true"), ("false", "false")],
                f"Value for {key}:",
                output=output,
                selected=preselected,
            )

        default = "" if (current is None or hide_current) else str(current)
        return ask_text(f"Value for {key}:", default=default, output=output).strip() or None

    @cli.command(name="list")
    @click.option('--query', '-q', help="Query to filter secrets")
    @click.option('--regex', '-g', is_flag=True, help="Use regex for filtering")
    def list(query: str | None = None, regex: bool = False):
        """List all key-value pairs in the config file.

        \b
        Example:
          $ ptools settings list --query PIP_EXECUTABLE
          PIP_EXECUTABLE: uv pip
        """
        data = filter_dict_by_key(config.list(), query, regex)

        # Empty State
        if not data or (isinstance(data, dict) and len(data) == 0):
            click.echo(FormatUtils.warning(f"No data found in config file {config.file_path}."))
            exit(1)

        # Table Output
        max_key_length = max(len(str(k)) for k in data.keys())
        for key, value in data.items():
            dump_one(str(key).ljust(max_key_length), value)

    @cli.command(name="get")
    @click.argument('key', required=False)
    def get(key):
        """Get the value of a key.

        When KEY is omitted, opens an interactive picker over the stored
        keys. The picker renders to the terminal even when stdout is a
        pipe, so ``VALUE=$(ptools settings get)`` still captures only the
        value.

        \b
        Example:
          $ ptools settings get PIP_EXECUTABLE
          uv pip
        """
        if key is None:
            key = pick_key("Select a key:", _picker_output())
            if key is None:
                exit(1)

        value = config.get(key)
        if value is not None:
            click.echo(value)
        else:
            exit(1)

    @cli.command(name="set")
    @click.argument('key', required=False)
    @click.argument('value', required=False)
    def set(key, value):
        """Set the value of a key.

        Omitting KEY opens a picker over the stored keys — plus, for a
        model-backed config, the fields it declares but hasn't stored yet
        and a "+ new key" row. Omitting VALUE prompts for one, pre-filled
        with the current value.

        \b
        Example:
          $ ptools settings set PIP_EXECUTABLE 'uv pip'
          Set 'PIP_EXECUTABLE' to 'uv pip'.
        """
        # Built only if something actually needs prompting, so a fully
        # scripted `set KEY VALUE` never reaches for a terminal.
        output = None
        if key is None:
            output = _picker_output()
            key = pick_key("Select a key to set:", output, include_unset=True, allow_new=True)
            if key is None:
                exit(1)

        if value is None:
            output = output if output is not None else _picker_output()
            value = ask_value(key, output)
            if value is None:
                exit(1)

        value = _coerce(config, key, value)
        config.set(key, value)
        click.echo(f"Set '{key}' to '{value}'.")

    @cli.command(name="delete")
    @click.argument('key', required=False)
    def delete(key):
        """Delete a key.

        When KEY is omitted, opens an interactive picker over the stored
        keys and confirms before removing the one chosen.

        \b
        Example:
          $ ptools settings delete PIP_EXECUTABLE
          Deleted key 'PIP_EXECUTABLE'.
        """
        if key is None:
            key = pick_key("Select a key to delete:", _picker_output())
            if key is None:
                exit(1)
            click.confirm(f"Delete '{key}'?", abort=True)

        if key not in config:
            click.echo(FormatUtils.warning(f"Key '{key}' not found in config file {config.file_path}."))
            exit(1)
        config.delete(key)
        click.echo(f"Deleted key '{key}'.")

    @cli.command(name="edit")
    def edit():
        """Browse and edit the config interactively.

        Loops: pick a key, choose what to do with it, then land back on a
        freshly-built picker so the effect of each change is visible.
        Escape at the key picker exits.
        """
        require_tty("'edit' requires an interactive terminal.")
        output = _picker_output()

        while True:
            key = pick_key(
                "Select a key to edit:",
                output,
                include_unset=True,
                allow_new=True,
            )
            if key is None:
                return

            action = select(
                [
                    ("set", f"Set the value of '{key}'"),
                    ("delete", f"Delete '{key}'"),
                    ("back", "Back to the key list"),
                ],
                f"What would you like to do with '{key}'?",
                output=output,
            )

            if action == "set":
                value = ask_value(key, output)
                if value is not None:
                    try:
                        value = _coerce(config, key, value)
                    except click.UsageError as e:
                        # Stay in the loop: a typo shouldn't drop the user
                        # out of the editor and lose their place.
                        click.echo(FormatUtils.error(e.format_message()), err=True)
                        continue
                    config.set(key, value)
                    click.echo(FormatUtils.success(f"Set '{key}' to '{value}'."))
            elif action == "delete":
                if key in config.data:
                    config.delete(key)
                    click.echo(FormatUtils.success(f"Deleted key '{key}'."))
                else:
                    click.echo(FormatUtils.warning(f"Key '{key}' is not stored; nothing to delete."))

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
