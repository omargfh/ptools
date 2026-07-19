"""Global settings for ptools.

Central place for configuration shared across :mod:`ptools` submodules.
Each setting is resolved in priority order:

1. Environment variable (highest - useful for one-off overrides)
2. Persistent global config file at ``~/.ptools/settings.json``
3. Hard-coded default (lowest)

Read settings by importing the module-level constants (``PIP_EXECUTABLE``,
etc.) or by calling :func:`get` directly. Both are resolved lazily on
first access (via a :pep:`562` module ``__getattr__``) rather than at
import time, so merely importing ``ptools.settings`` - or a submodule
that imports it - never reads or creates ``~/.ptools/settings.json``.
Persist a setting across shells with :func:`set` - that writes to the
config file so it survives without needing an env var::

    from ptools import settings
    settings.set("PIP_EXECUTABLE", "uv pip")

A single env var still wins over the stored value, so you can temporarily
override without losing the persisted default::

    PIP_EXECUTABLE="pip3" ptools dev install
"""

import os
import sys

from ptools.utils.config import LazyConfigFile, config_to_CLI
from ptools.utils.shell import detect_shell, detect_shell_config, detect_shell_kind
from pydantic import BaseModel, Field

class SettingsModel(BaseModel):
    """Pydantic model for validating settings values.

    Field defaults here are the hard-coded (lowest-priority) tier only -
    the env-var tier is applied by :func:`get`, not baked in as a field
    default, so mutating ``os.environ`` after import still takes effect.
    ``SHELL_EXECUTABLE``/``SHELL_CONFIG`` use ``default_factory`` so the
    shell-detection subprocess calls stay lazy (run at validation time,
    not at class/import time).
    """

    PIP_EXECUTABLE: str = f"{sys.executable} -m pip"
    PTOOLS_DEBUG: bool = False
    EDITOR: str = "vim"
    SHELL_EXECUTABLE: str = Field(default_factory=detect_shell)
    SHELL_CONFIG: str = Field(default_factory=detect_shell_config)
    VAULT_IN_PLACE: bool = True

# Field name -> env var name, for the two fields whose env var differs
# from the field name (settings.py:37-38 historically).
_ENV_VAR_NAMES = {
    "PIP_EXECUTABLE": "PIP_EXECUTABLE",
    "PTOOLS_DEBUG": "PTOOLS_DEBUG",
    "EDITOR": "EDITOR",
    "SHELL_EXECUTABLE": "PTOOLS_SHELL",
    "SHELL_CONFIG": "PTOOLS_SHELL_CONFIG",
    "VAULT_IN_PLACE": "VAULT_IN_PLACE",
}

settings = LazyConfigFile("settings", quiet=True, model=SettingsModel)
cli = config_to_CLI(settings, name="settings")


def get(name):
    """Resolve *name* by precedence: env var, then the persisted file,
    then the hard-coded default -- matching the module docstring above.

    Evaluated at call time (not import time), so a change to
    ``os.environ`` after ``ptools.settings`` was imported still affects
    the next call. Never writes the resolved value back to disk - only
    :func:`set` persists.
    """
    env_name = _ENV_VAR_NAMES.get(name, name)
    if env_name in os.environ:
        value = os.environ[env_name]
        field = SettingsModel.model_fields.get(name)
        if field is not None and field.annotation is bool:
            # Keep the exact truthiness rule the old field default used:
            # only "1" is true, so e.g. PTOOLS_DEBUG=true stays false.
            return value == "1"
        return value

    if name in settings.data:
        return settings.data[name]

    field = SettingsModel.model_fields.get(name)
    if field is not None:
        return field.get_default(call_default_factory=True)
    return None


def set(name, value):
    """Persist *name* = *value* to ``~/.ptools/settings.json``.

    An env var still overrides the stored value for the current
    shell/session (see :func:`get`); this is what makes a value survive
    across sessions without one.
    """
    return settings.set(name, value)


# Names resolved lazily via __getattr__ below rather than assigned here:
# assigning them at module scope would force settings.data (and so the
# LazyConfigFile's disk read/create) on every import of this module,
# which is exactly the eager cost LazyConfigFile exists to avoid.
_MODULE_CONSTANTS = frozenset({
    "PIP_EXECUTABLE", "PTOOLS_DEBUG", "EDITOR", "SHELL_EXECUTABLE", "SHELL_CONFIG",
    "VAULT_IN_PLACE",
})


def __getattr__(name):
    """:pep:`562` module attribute access for the settings constants.

    Only fires when *name* isn't already a real module attribute, and
    only then calls :func:`get` (or, for ``SHELL_KIND``, derives it from
    ``SHELL_EXECUTABLE``) - so ``import ptools.settings`` alone never
    touches ``settings.data``, but ``ptools.settings.EDITOR`` still
    resolves the current env/persisted/default value on demand.
    """
    if name in _MODULE_CONSTANTS:
        return get(name)
    if name == "SHELL_KIND":
        return detect_shell_kind(get("SHELL_EXECUTABLE"))
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")