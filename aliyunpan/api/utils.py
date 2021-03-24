import asyncio
import functools
import hashlib
import logging
import os

__all__ = ['ROOT_DIR', 'logger', 'async_run_sync', 'run', 'StrOfSize']
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(ROOT_DIR))
LOG_LEVEL = logging.INFO
logger = logging.getLogger('aliyunpan')
log_file = ROOT_DIR + os.sep + 'aliyunpan.log'
fmt_str = "%(asctime)s [%(filename)s:%(lineno)d] %(funcName)s %(levelname)s - %(message)s"
logging.basicConfig(level=LOG_LEVEL,
                    filename=log_file,
                    filemode="a",
                    format=fmt_str,
                    datefmt="%Y-%m-%d %H:%M:%S")
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_sha1(path, split_size):
    with open(path, 'rb') as f:
        sha1 = hashlib.sha1()
        count = 0
        while True:
            chunk = f.read(split_size)
            if not chunk:
                break
            count += 1
            sha1.update(chunk)
        content_hash = sha1.hexdigest()
    return content_hash


async def async_run_sync(fun, async_timeout):
    loop = asyncio.get_event_loop()
    return await asyncio.wait_for(loop.run_in_executor(None, fun), async_timeout)


def run(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'async_run' in kwargs and kwargs['async_run']:
            kwargs.pop('async_run')
            return f(*args, **kwargs)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(f(*args, **kwargs))

    return decorated


def StrOfSize(size):
    def strofsize(integer, remainder, level):
        if integer >= 1024:
            remainder = integer % 1024
            integer //= 1024
            level += 1
            return strofsize(integer, remainder, level)
        else:
            return integer, remainder, level

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    integer, remainder, level = strofsize(size, 0, 0)
    if level + 1 > len(units):
        level = -1
    return ('{}.{:>03d}{}'.format(integer, remainder, units[level]))
