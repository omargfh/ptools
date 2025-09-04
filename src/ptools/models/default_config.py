from pydantic import BaseModel
from typing import List

from ptools.utils.config import ConfigFile

class DefaultConfig(BaseModel):
    verbose: bool = False

def load_default_config() -> ConfigFile:
    """Loads, validates, and fills defaults for the default configuration."""
    default_config = ConfigFile("ptools", quiet=True)
    config_data = DefaultConfig(**default_config.data)
   
    for k, v in config_data.model_dump().items():
        if k not in default_config.data:
            default_config.set(k, v)

    return default_config
