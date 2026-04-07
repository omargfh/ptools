"""Lightweight serialization helpers for JSON and YAML.

Re-exports :mod:`ptools.formats.json` and :mod:`ptools.formats.yaml`
under the shortened names :obj:`json` and :obj:`yaml` so callers can do::

    from ptools import formats
    formats.yaml.dump(obj)
    formats.json.load(path)
"""

import ptools.formats.yaml as yaml
import ptools.formats.json as json
