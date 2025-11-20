class SeralizerDeserializer:
    name = ''
    ext = ''
    exts = ()
    DecodeError = Exception

    @staticmethod
    def dumps(self, data, **opts):
        raise NotImplementedError

    @staticmethod
    def loads(self, data, **opts):
        raise NotImplementedError

    @staticmethod
    def dump(data, file, **opts):
        raise NotImplementedError

    @staticmethod
    def load(file, **opts):
        raise NotImplementedError

class JSONSerializerDeserializer(SeralizerDeserializer):
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
    @staticmethod
    def get(format):
        format = format.lower()
        if format == 'json':
            return JSONSerializerDeserializer
        elif format in ['yaml', 'yml']:
            return YAMLSerializerDeserializer
        else:
            raise ValueError(f"Unsupported format: {format}")