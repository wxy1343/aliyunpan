from pathlib import Path

from ruamel.yaml import YAML

__all__ = ['Config']
yaml = YAML()


class Config:
    def __init__(self, config_file=None):
        self._config_file = config_file

    config_file = property(lambda self: self._config_file,
                           lambda self, value: setattr(self, '_config_file', Path(value)))

    def _read(self):
        with open(self.config_file) as f:
            return yaml.load(f) or False

    def _write(self, conf):
        with open(self.config_file, 'w') as f:
            yaml.dump(conf, f)
        return True

    def get(self, key):
        conf = self._read()
        if not conf:
            raise FileNotFoundError('Configuration file error.')
        if key in conf.keys():
            value = conf.get(key)
            return value
        return False

    def update(self, key, value):
        conf = self._read() or {}
        conf.update({key: value})
        self._write(conf)
        return conf

    def delete(self, key):
        conf = self._read() or {}
        if conf and key in conf:
            conf.pop(key)
            self._write(conf)
        return True
