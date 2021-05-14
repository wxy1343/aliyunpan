__all__ = ['DATA', 'GLOBAL_VAR', 'Printer']


class DATA(dict):
    def __init__(self, seq=None, **kwargs):
        if not seq:
            seq = {}
        super(DATA, self).__init__(seq, **kwargs)
        for key, value in seq.items():
            if isinstance(value, dict):
                self[key] = DATA(value)
            else:
                self[key] = value

    def to_dict(self):
        dict_ = {}
        for key, value in self.items():
            if isinstance(value, DATA):
                dict_[key] = value.to_dict()
            else:
                dict_[key] = value
        return dict_

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None

    def __setattr__(self, key, value):
        if isinstance(value, dict):
            self[key] = DATA(value)
        else:
            self[key] = value

    def __delattr__(self, item):
        del self[item]

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            super(DATA, self).__setitem__(key, DATA(value))
        else:
            super(DATA, self).__setitem__(key, value)


GLOBAL_VAR = DATA()
GLOBAL_VAR.tasks = {}
GLOBAL_VAR.file_hash_list = set()


class Printer(object):
    instance = None

    def __new__(cls, *args, **kwargs):
        if not cls.instance:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self, *args, **kwargs):
        self._info = '[{}]'
        self._start_flag = '*'
        self._success_flag = '+'
        self._fail_flag = '-'
        self._existed_title = 'existed'
        self._upload_title = 'upload'
        self._rapid_upload_title = 'rapid'
        self._download_title = 'download'
        self._mkdir_info = 'mkdir'
        self._move_info = 'mv'
        self._remove_info = 'rm'

    def get_flag(self, status):
        if status is None:
            return self._start_flag
        elif status is True:
            return self._success_flag
        elif status is False:
            return self._fail_flag
        else:
            return status

    def get_info(self, status, *args):
        info = self._info.format(self.get_flag(status))
        for i in args:
            if i:
                info += self._info.format(i)
        return info

    def upload_info(self, path, status=None, rapid_upload=False, time=None, average_speed=None, existed=False):
        time = 'time:{}'.format(time) if time else None
        average_speed = 'avg:{}'.format(average_speed) if average_speed else None
        rapid_title = self._rapid_upload_title if rapid_upload else None
        if existed:
            existed_title = self._existed_title
        else:
            existed_title = None
        info = self.get_info(status, self._upload_title, existed_title, rapid_title, time, average_speed) + str(path)
        print(info)

    def download_info(self, path, status=None):
        info = self.get_info(status, self._download_title) + str(path)
        print(info)

    def mkdir_info(self, path, status=None):
        info = self.get_info(status, self._mkdir_info) + str(path)
        print(info)

    def move_info(self, path, target_path, status=None):
        info = self.get_info(status, self._move_info) + str(path) + ' -> ' + str(target_path)
        print(info)

    def remove_info(self, path, status=None):
        info = self.get_info(status, self._remove_info) + str(path)
        print(info)
