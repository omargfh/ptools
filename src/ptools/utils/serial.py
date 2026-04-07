"""Pluggable serializer/deserializer adapters used by the config module."""

__version__ = "0.1.0"


class SeralizerDeserializer:
    """Abstract serializer base class.

    Concrete subclasses populate :attr:`name`, :attr:`ext`, :attr:`exts`
    and :attr:`DecodeError`, then implement the four (de)serialization
    methods. The factory below picks one based on a format string.
    """

    name = ''
    ext = ''
    exts = ()
    DecodeError = Exception

    @staticmethod
    def dumps(data, **opts):
        """Serialize ``data`` to a string."""
        raise NotImplementedError

    @staticmethod
    def loads(data, **opts):
        """Deserialize ``data`` from a string."""
        raise NotImplementedError

    @staticmethod
    def dump(data, file, **opts):
        """Serialize ``data`` directly into the open ``file`` handle."""
        raise NotImplementedError

    @staticmethod
    def load(file, **opts):
        """Deserialize the contents of the open ``file`` handle."""
        raise NotImplementedError

class JSONSerializerDeserializer(SeralizerDeserializer):
    """JSON adapter (4-space indented) backed by the stdlib :mod:`json` module."""
    import json

    name = 'JSON'
    ext = 'json'
    exts = ('json',)
    DecodeError = json.JSONDecodeError

    @staticmethod
    def dumps(data, **opts):
        return JSONSerializerDeserializer.json.dumps(data, indent=4, **opts)

    @staticmethod
    def loads(data, **opts):
        return JSONSerializerDeserializer.json.loads(data, **opts)

    @staticmethod
    def dump(data, file, **opts):
        return JSONSerializerDeserializer.json.dump(data, file, indent=4, **opts)

    @staticmethod
    def load(file, **opts):
        return JSONSerializerDeserializer.json.load(file, **opts)

class YAMLSerializerDeserializer(SeralizerDeserializer):
    """YAML adapter using PyYAML's safe loader and a unicode-friendly dumper."""
    import yaml

    name = 'YAML'
    ext = 'yaml'
    exts = ('yaml', 'yml')
    DecodeError = yaml.YAMLError
    default_dump_opts = {
      'default_flow_style': False,
      'allow_unicode': True,
      'width': 120,
      'indent': 2,
      'sort_keys': False
    }

    @staticmethod
    def dumps(data, **opts):
        myself = YAMLSerializerDeserializer
        kwargs = {**myself.default_dump_opts, **opts}
        return myself.yaml.dump(data, **kwargs)

    @staticmethod
    def loads(data):
        myself = YAMLSerializerDeserializer
        return myself.yaml.safe_load(data)

    @staticmethod
    def dump(data, file, **opts):
        myself = YAMLSerializerDeserializer
        kwargs = {**myself.default_dump_opts, **opts}
        return myself.yaml.dump(data, file, **kwargs)

    @staticmethod
    def load(file):
        myself = YAMLSerializerDeserializer
        return myself.yaml.safe_load(file)

class SerializerDeserializerFactory:
    """Resolve a serializer adapter class from a short format name."""

    @staticmethod
    def get(format):
        """Return the adapter class for ``format`` (``"json"``, ``"yaml"``, ``"yml"``).

        :raises ValueError: if ``format`` is not supported.
        """
        format = format.lower()
        if format == 'json':
            return JSONSerializerDeserializer
        elif format in ['yaml', 'yml']:
            return YAMLSerializerDeserializer
        else:
            raise ValueError(f"Unsupported format: {format}")