import base64
import ctypes
import hashlib
import inspect
import json
import logging
import os
import socket
import sys

import rsa

__all__ = ['ROOT_DIR', 'logger', 'log_file', 'get_sha1', 'str_of_size', 'Iter', 'encrypt', 'parse_biz_ext',
           'stop_thread', 'get_open_port']

ROOT_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
LOG_LEVEL = logging.INFO
logger = logging.getLogger('aliyunpan')
log_file = ROOT_DIR + os.sep + 'aliyunpan.log'
fmt_str = "%(asctime)s [%(filename)s:%(lineno)d] %(funcName)s %(levelname)s - %(message)s"
logging.basicConfig(level=LOG_LEVEL,
                    format=fmt_str,
                    stream=open(log_file, 'a', encoding='utf-8'),
                    datefmt="%Y-%m-%d %H:%M:%S")
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_sha1(path, split_size=524288):
    logger.info(f'Calculate sha1 of file {path}.')
    file_size = os.path.getsize(path)
    from aliyunpan.common import HashBar
    hash_bar = HashBar(size=file_size)
    hash_bar.hash_info(path, size=file_size)
    hash_bar.print_line()
    hash_bar.update(refresh_line=False)
    with open(path, 'rb') as f:
        sha1 = hashlib.sha1()
        count = 0
        while True:
            chunk = f.read(split_size)
            k = ((count * split_size) + len(chunk)) / file_size if file_size else 0
            hash_bar.update(ratio=k, refresh_line=True)
            if not chunk:
                break
            count += 1
            sha1.update(chunk)
        content_hash = sha1.hexdigest()
    logger.info(f'The SHA1 of file {path} is {content_hash}.')
    hash_bar.refresh_line()
    hash_bar.hash_info(path, status=True, size=file_size, refresh_line=True)
    hash_bar.print_line()
    return content_hash


def str_of_size(size, decimal=3, tuple_=False):
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    integer = int(size)
    level = 0
    while integer >= 1024:
        integer //= 1024
        level += 1
    if level + 1 > len(units):
        level = -1
    size = round(size / (1024 ** level), decimal) if decimal else size
    if tuple_:
        return size, units[level]
    return f'{size}{units[level]}'


class Iter:

    def __init__(self, IterObj):
        self.iter = IterObj

    def __getitem__(self, index):
        return self.iter[index]

    def __len__(self):
        return len(self.iter)


# RSA encrypt
PUBLIC_KEY = b'-----BEGIN PUBLIC KEY-----\n' \
             b'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDTvO8fAEJPMmHIkyP6jN+hK7rE\n' \
             b'ANn+i7Yn6NJ6RL1dWdzlWRNdZ4qBQ761uNcFbE4ficTh8VJHBiW3tBlEqX8C2m9g\n' \
             b'WkmpPsbrnLry56wrJqNUzmnrJllT0sKeOV1tjBzbaIl4VRqg91IfKQA1+tOBF42g\n' \
             b'vqj55q3OOQIPUTEz+wIDAQAB\n' \
             b'-----END PUBLIC KEY-----'


def encrypt(password):
    MAP = "0123456789abcdefghijklmnopqrstuvwxyz"
    rsa_result = rsa.encrypt(
        password.encode(),
        rsa.PublicKey.load_pkcs1_openssl_pem(PUBLIC_KEY)
    )
    ans = ''
    for byte in rsa_result:
        ans += MAP[byte >> 4]
        ans += MAP[byte & 0x0F]
    return ans


def parse_biz_ext(biz_ext):
    biz_ext = base64.b64decode(biz_ext).decode('gbk')
    logger.debug(biz_ext)
    return json.loads(biz_ext)


def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


def get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port
