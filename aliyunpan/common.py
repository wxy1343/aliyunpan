import os
import sys
import time
from abc import abstractmethod
from threading import RLock

from colorama import Fore, Style, Back

from aliyunpan.api.utils import str_of_size

__all__ = ['DATA', 'GLOBAL_VAR', 'Printer', 'Bar', 'FileBar', 'UploadBar', 'DownloadBar', 'HashBar']
os.system('')


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
GLOBAL_VAR.file_set = set()


class Info:
    def __init__(self, info='', error=False, refresh_line=False, color=None):
        self.info = info
        self.error = error
        self.color = color
        if not self.color and self.error:
            self.color = Fore.RED
        self.refresh_line = refresh_line

    def __str__(self):
        info = self.info
        if self.color:
            info = Style.BRIGHT + Back.BLACK + self.color + info + Style.RESET_ALL
        if self.refresh_line:
            info = '\r' + info
        return info

    def __repr__(self):
        return self.__str__().__repr__()

    def __len__(self):
        return len(self.__str__())


class Flag:
    def __init__(self, status):
        self._start_flag = '*'
        self._success_flag = '+'
        self._fail_flag = '-'
        if status is None:
            self._flag = self._start_flag
            self.color = Fore.LIGHTYELLOW_EX
        elif status is True:
            self._flag = self._success_flag
            self.color = Fore.LIGHTGREEN_EX
        elif status is False:
            self._flag = self._fail_flag
            self.color = Fore.RED
        else:
            self._flag = status
            self.color = None

    def __str__(self):
        return self._flag


class OutPut(object):
    def __init__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        self._stdin = sys.stdin
        self._lock = RLock()

    @property
    @abstractmethod
    def output(self):
        pass

    @output.setter
    @abstractmethod
    def output(self, value):
        pass


class OutPutSingleton(OutPut):
    _instance = None
    _first_init = True

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._first_init:
            return
        self._first_init = False
        super(OutPutSingleton, self).__init__()
        self._print = self._output_gen()
        self._print.__next__()
        self.print_line = False

    def __del__(self):
        self._stdout.write('\n')

    output = property(lambda self: self._print,
                      lambda self, value: (self._lock.acquire(), setattr(self, '_', None),
                                           self._print.send(value), self._lock.release())[1])

    def _output_gen(self):
        last_info = None
        while True:
            info = yield
            with self._lock:
                if self.print_line:
                    self._stdout.write('\n')
                    self.print_line = False
                if last_info:
                    if info.refresh_line:
                        if len(last_info) > len(info):
                            self._stdout.write('\r' + len(last_info) * ' ')
                if info.error:
                    self._stderr.write(str(info))
                else:
                    self._stdout.write(str(info))
                self._stderr.flush()
                self._stdout.flush()
            last_info = info


class Printer(OutPut):
    def __init__(self):
        super(Printer, self).__init__()
        self._info = '[{}]'
        self._existed_title = 'existed'
        self._upload_title = 'upload'
        self._rapid_upload_title = 'rapid'
        self._download_title = 'download'
        self._mkdir_title = 'mkdir'
        self._move_title = 'mv'
        self._link_info = ' -> '
        self._remove_title = 'rm'
        self._rename_title = 'rename'
        self._hash_title = 'hash'
        self._time_info = 'time:{:.2f}s'
        self.avg_info = 'avg:{:.2f}{}/s'
        self._error_info = 'Error:{}'
        self._aria2_title = 'aria2'
        self._mkdir_color = Fore.LIGHTCYAN_EX
        self._move_color = Fore.LIGHTMAGENTA_EX
        self._remove_color = Fore.LIGHTRED_EX
        self._rename_color = Fore.LIGHTBLUE_EX
        self._wait_color = Fore.MAGENTA
        self._error_color = Fore.RED
        self._print = OutPutSingleton()
        self._hash_size = 1024 ** 3
        self._output = True

    output = property(lambda self: self._print.output,
                      lambda self, value: (
                          self._lock.acquire(), setattr(self._print, 'output', value),
                          self._lock.release())[1] if self._output else None)

    def get_info(self, status, path, *args, existed=False, target_path=None, refresh_line=False):
        path_info = str(path) + self._link_info + str(target_path) if target_path else str(path)
        flag = Flag(status)
        info = self._info.format(flag)
        if existed:
            args = (*args[:1], self._existed_title, *args[1:])
        for i in args:
            if i:
                info += self._info.format(i)
        info = Info(info=info + path_info, error=status is False, refresh_line=refresh_line)
        info.color = flag.color
        return info

    def error_info(self, info, refresh_line=False):
        self.output = Info(self._error_info.format(info), color=self._error_color, error=True,
                           refresh_line=refresh_line)

    def wait_info(self, title=None, t=3, refresh_line=False):
        while t > 0:
            self.output = Info((title or '{time}秒后重试').format(time=t), color=self._wait_color,
                               refresh_line=refresh_line)
            t -= 1
            time.sleep(1)

    def upload_info(self, path, status=None, refresh_line=False, rapid_upload=False, t=None, average_speed=None, *args,
                    **kwargs):
        t = self._time_info.format(t) if t else None
        average_speed = self.avg_info.format(*str_of_size(average_speed, tuple_=True)) if average_speed else None
        rapid_title = self._rapid_upload_title if rapid_upload else None
        info = self.get_info(status, path, self._upload_title, rapid_title, t, average_speed, *args,
                             refresh_line=refresh_line, **kwargs)
        self.output = info

    def download_info(self, path, status=None, refresh_line=False, t=None, average_speed=None, aria2=False, *args):
        t = self._time_info.format(t) if t else None
        aria2 = self._aria2_title if aria2 else aria2
        average_speed = self.avg_info.format(*str_of_size(average_speed, tuple_=True)) if average_speed else None
        info = self.get_info(status, path, self._download_title, aria2, t, average_speed, *args,
                             refresh_line=refresh_line)
        self.output = info

    def mkdir_info(self, path, status=None, *args, **kwargs):
        info = self.get_info(status, path, self._mkdir_title, *args, **kwargs)
        info.color = self._mkdir_color or info.color
        self.output = info

    def move_info(self, path, target_path, status=None, *args, **kwargs):
        info = self.get_info(status, path, self._move_title, *args, target_path=target_path, **kwargs)
        info.color = self._move_color or info.color
        self.output = info

    def remove_info(self, path, status=None, *args, **kwargs):
        info = self.get_info(status, path, self._remove_title, *args, **kwargs)
        info.error = False
        info.color = self._remove_color or info.color
        self.output = info

    def rename_info(self, path, name, status=None, *args, **kwargs):
        info = self.get_info(status, path, self._rename_title, *args, target_path=name, **kwargs)
        info.color = self._rename_color or info.color
        self.output = info

    def hash_info(self, path, status=None, size=None, *args, **kwargs):
        info = self.get_info(status, path, self._hash_title, *args, **kwargs)
        self.output = info

    def refresh_line(self):
        if self._output:
            self._print.print_line = False
        self.output = Info(refresh_line=True)

    def print_line(self):
        if self._output:
            self._print.print_line = True

    def print_info(self, info, error=False, refresh_line=False, *args, **kwargs):
        self.output = Info(info, error, refresh_line, *args, **kwargs)


class Bar(Printer):
    def __init__(self, title=None, refresh_interval=0.3):
        super(Bar, self).__init__()
        self._title = title or self.__class__.__name__
        self._upload_info = '{title}{:<3s} [{}{}] {:.2%} {:.2f}{unit}/s'
        self._ratio = 0.0
        self._start_time = time.time()
        self._time = time.time()
        self._average_speed = 0
        self._count = 0
        self._update_time = 0
        self._unit = 'it'
        self.refresh_interval = refresh_interval

    time = property(lambda self: time.time() - self._start_time)
    average_speed = property(lambda self: self._size / self.time if self.time else 0)

    def _get_average_speed(self, ratio, t):
        return (ratio - self._ratio) / t if t else 0

    def _format(self, *args, **kwargs):
        kwargs.setdefault('unit', self._unit)
        speed, unit = str_of_size(self._average_speed, tuple_=True)
        if not kwargs['unit']:
            kwargs['unit'] = unit
        return self._upload_info.format('.' * (4 - (self._count % 3 or 3)), '=' * int(self._ratio * 10),
                                        '*' * (10 - int(self._ratio * 10)), self._ratio,
                                        speed, title=self._title, *args, **kwargs)

    def update(self, ratio=None, refresh_line=False):
        self._count += 1
        t = 0
        if ratio is not None:
            t = time.time() - self._time
            self._time = time.time()
            average_speed = self._get_average_speed(ratio, t)
            if self._ratio != ratio and average_speed is not None:
                self._average_speed = average_speed
                self._ratio = ratio
        if t and time.time() - self._update_time >= self.refresh_interval:
            self._update_time = time.time()
            upload_info = self._format()
            self.output = Info(upload_info, refresh_line=refresh_line, color=Fore.LIGHTMAGENTA_EX)


class GetFileListBar(Bar):
    def __init__(self, max_depth, *args, **kwargs):
        super(GetFileListBar, self).__init__(*args, **kwargs)
        self._max_depth = max_depth
        self._depth = 0
        self._upload_info = '{title}{:<3s} [{}{}] {:.2%} [{depth}/{max_depth}] {:.2f}{unit}/s'
        self._title = 'get_file_list'
        self._time_out = 5
        self.refresh_interval = 0
        self._output = False

    def update(self, depth=0, *args, **kwargs):
        self._depth = depth
        if self.time > self._time_out:
            self._output = True
        super(GetFileListBar, self).update(*args, **kwargs)

    def _format(self, *args, **kwargs):
        return super(GetFileListBar, self)._format(depth=self._depth, max_depth=self._max_depth, *args, **kwargs)

    def _get_average_speed(self, ratio, t):
        if t:
            return super(GetFileListBar, self)._get_average_speed(ratio, t)


class FileBar(Bar):
    def __init__(self, title=None, size=0, *args, **kwargs):
        super(FileBar, self).__init__(*args, **kwargs)
        self._file_size = 1024 * 1024
        self._title = title or self.__class__.__name__
        self._size = size
        self._unit = None
        if self._size < self._file_size:
            self._output = False

    def _get_average_speed(self, ratio, t):
        return self._size * super(FileBar, self)._get_average_speed(ratio, t)


class UploadBar(FileBar):
    def __init__(self, size, *args, **kwargs):
        super(UploadBar, self).__init__(size=size, *args, **kwargs)
        self._title = self._upload_title


class DownloadBar(FileBar):
    def __init__(self, size, *args, **kwargs):
        super(DownloadBar, self).__init__(size=size, *args, **kwargs)
        self._title = self._download_title


class HashBar(FileBar):
    def __init__(self, size, *args, **kwargs):
        super(HashBar, self).__init__(size=size, *args, **kwargs)
        self._title = self._hash_title
        self._size = size
        self._time_out = 5
        if self._size < self._hash_size:
            self._output = False

    def update(self, *args, **kwargs):
        if self.time > self._time_out:
            self._output = True
        super(HashBar, self).update(*args, **kwargs)

    def hash_info(self, *args, **kwargs):
        super(HashBar, self).hash_info(*args, **kwargs)
