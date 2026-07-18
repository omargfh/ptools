"""Global settings for ptools.

Central place for configuration shared across :mod:`ptools` submodules.
Each setting is resolved in priority order:

1. Environment variable (highest - useful for one-off overrides)
2. Persistent global config file at ``~/.ptools/settings.json``
3. Hard-coded default (lowest)

Read settings by importing the module-level constants (``PIP_EXECUTABLE``,
etc.) or by calling :func:`get` directly. Persist a setting across shells
with :func:`set` - that writes to the config file so it survives without
needing an env var::

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
from pydantic import BaseModel

class SettingsModel(BaseModel):
    """Pydantic model for validating settings values."""

    PIP_EXECUTABLE: str = os.environ.get("PIP_EXECUTABLE", f"{sys.executable} -m pip")
    PTOOLS_DEBUG: bool = os.environ.get("PTOOLS_DEBUG", "0") == "1"
    EDITOR: str = os.environ.get("EDITOR", "vim")
    SHELL_EXECUTABLE: str = os.environ.get("PTOOLS_SHELL", detect_shell())
    SHELL_CONFIG: str = os.environ.get("PTOOLS_SHELL_CONFIG", detect_shell_config())

settings = LazyConfigFile("settings", quiet=True, model=SettingsModel)
cli = config_to_CLI(settings, name="settings")

if __name__ != "__main__":
    PIP_EXECUTABLE = settings.typed.PIP_EXECUTABLE
    PTOOLS_DEBUG = settings.typed.PTOOLS_DEBUG
    EDITOR = settings.typed.EDITOR
    SHELL_EXECUTABLE = settings.typed.SHELL_EXECUTABLE
    SHELL_CONFIG = settings.typed.SHELL_CONFIG
    SHELL_KIND = detect_shell_kind(SHELL_EXECUTABLE)
else:
    cli = config_to_CLI(settings, name="settings")