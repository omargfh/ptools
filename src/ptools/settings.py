"""Global settings for ptools.

Central place for configuration shared across :mod:`ptools` submodules.
Each setting is resolved in priority order:

1. Environment variable (highest — useful for one-off overrides)
2. Persistent global config file at ``~/.ptools/settings.json``
3. Hard-coded default (lowest)

Read settings by importing the module-level constants (``PIP_EXECUTABLE``,
etc.) or by calling :func:`get` directly. Persist a setting across shells
with :func:`set_` — that writes to the config file so it survives without
needing an env var::

    from ptools import settings
    settings.set_("PIP_EXECUTABLE", "uv pip")

A single env var still wins over the stored value, so you can temporarily
override without losing the persisted default::

    PIP_EXECUTABLE="pip3" ptools dev install
"""

import os
import sys

from ptools.utils.config import  LazyConfigFile, config_to_CLI
from pydantic import BaseModel

class SettingsModel(BaseModel):
    """Pydantic model for validating settings values."""

    PIP_EXECUTABLE: str = os.environ.get("PIP_EXECUTABLE", f"{sys.executable} -m pip")


settings = LazyConfigFile("settings", quiet=True, model=SettingsModel)
cli = config_to_CLI(settings, name="settings")

if __name__ != "__main__":
    PIP_EXECUTABLE = settings.typed.PIP_EXECUTABLE
else:
    cli = config_to_CLI(settings, name="settings")