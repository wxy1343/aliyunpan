from pathlib import Path

from ruamel.yaml import YAML

from aliyunpan.common import DATA
from aliyunpan.exceptions import InvalidConfiguration

__all__ = ['Config']

yaml = YAML()


class Config:
    def __init__(self, config_file=None):
        self._config_file = Path(config_file) if config_file else None

    config_file = property(lambda self: self._config_file,
                           lambda self, value: setattr(self, '_config_file', Path(value)))

    def read(self):
        try:
            if not self._config_file or not self._config_file.is_file():
                return {}
        except TypeError:
            return {}
        with self.config_file.open(encoding='utf-8') as f:
            return yaml.load(f) or {}

    def write(self, conf):
        if not conf:
            try:
                self._config_file.unlink()
            except FileNotFoundError:
                pass
            return
        try:
            if not self._config_file or not self._config_file.is_file():
                if not self._config_file.parent.is_dir():
                    self._config_file.parent.mkdir(parents=True)
                self._config_file.touch()
        except TypeError:
            return
        if isinstance(conf, DATA):
            conf = conf.to_dict()
        with self.config_file.open('w', encoding='utf-8') as f:
            yaml.dump(conf, f)
        return True

    def get(self, key):
        if not self._config_file:
            return False
        conf = self.read()
        try:
            if key in conf.keys():
                value = conf.get(key)
                return value
        except AttributeError:
            raise InvalidConfiguration
        return None

    def update(self, key, value):
        if not self._config_file:
            return False
        conf = self.read() or {}
        if isinstance(value, DATA):
            value = dict(value)
        if value is None:
            del conf[key]
        else:
            conf.update({key: value})
        if conf:
            self.write(conf)
        else:
            self._config_file.unlink()
        return conf

    def delete(self, key):
        if not self._config_file:
            return False
        conf = self.read() or {}
        if conf and key in conf:
            conf.pop(key)
            self.write(conf)
        return True
