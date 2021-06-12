from pathlib import Path

from ruamel.yaml import YAML

from aliyunpan.common import DATA

__all__ = ['Config']

yaml = YAML()


class Config:
    def __init__(self, config_file=None):
        self._config_file = Path(config_file) if config_file else None

    config_file = property(lambda self: self._config_file,
                           lambda self, value: setattr(self, '_config_file', Path(value)))

    def read(self):
        if not self._config_file.is_file():
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
        if not self._config_file.is_file():
            if not self._config_file.parent.is_dir():
                self._config_file.parent.mkdir(parents=True)
            self._config_file.touch()
        if isinstance(conf, DATA):
            conf = conf.to_dict()
        with self.config_file.open('w', encoding='utf-8') as f:
            yaml.dump(conf, f)
        return True

    def get(self, key):
        conf = self.read()
        if key in conf.keys():
            value = conf.get(key)
            return value
        return None

    def update(self, key, value):
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
        conf = self.read() or {}
        if conf and key in conf:
            conf.pop(key)
            self.write(conf)
        return True
