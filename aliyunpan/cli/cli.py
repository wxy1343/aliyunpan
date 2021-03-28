import math
import os
import sys
import time

import requests

from aliyunpan.api.core import AliyunPan
from aliyunpan.api.models import PathList
from aliyunpan.api.req import *
from aliyunpan.api.utils import *

__all__ = ['Commander']


class Commander:
    def __init__(self):
        self._disk = AliyunPan()
        self._path_list = PathList(self._disk)
        self._req = Req()
        self.refresh_token = ''

    def disk_init(self, refresh_token):
        if len(refresh_token) == 32:
            self._disk.refresh_token = refresh_token
        else:
            raise Exception('Is not a valid refresh_token')

    def ls(self, path, l):
        self._path_list.get_path_list(path)
        for i in self._path_list.get_path_list(path):
            if l:
                if i.type:
                    print(StrOfSize(i.size), time.strftime('%d %b %H:%M', i.ctime), i.id, i.name)
                else:
                    print('-', time.strftime('%d %b %H:%M', i.ctime), i.id, i.name)
            else:
                print(i.name, end='\t')

    def tree(self, path):
        self._path_list.tree(path)

    def rm(self, path):
        self._disk.delete_file(self._path_list.get_path_fid(path))

    def mv(self, path, parent_path):
        self._disk.move_file(self._path_list.get_path_fid(path), self._path_list.get_path_fid(parent_path))

    def upload(self, upload_path, path_list, timeout, retry, force):
        for path in path_list:
            if path:
                if os.path.isfile(path):
                    self._disk.upload_file(self._path_list.get_path_fid(upload_path), path, timeout, retry, force)
                elif os.path.isdir(path):
                    if upload_path == 'root':
                        upload_path = '/'
                    self.upload_dir(path, upload_path, timeout, retry, force)
                else:
                    raise FileNotFoundError

    def upload_dir(self, path, upload_path, timeout, retry, force):
        if not self._path_list.get_path_fid(os.path.join(upload_path, os.path.split(path)[1]).replace('\\', '/')):
            if upload_path == '/':
                self._disk.create_file(os.path.split(path)[1], upload_path)
            else:
                self._disk.create_file(os.path.split(path)[1], self._path_list.get_path_fid(upload_path))
        upload_path = os.path.join(upload_path, os.path.split(path)[1]).replace('\\', '/')
        for file in os.listdir(path):
            p = os.path.join(path, file)
            if os.path.isdir(p):
                self.upload_dir(p, upload_path, timeout, retry, force)
            else:
                self._disk.upload_file(self._path_list.get_path_fid(upload_path), p, timeout, retry, force)

    def download(self, path_list, save_path):
        if save_path == '':
            save_path = os.getcwd()
        for path in path_list:
            if isinstance(path, str):
                file_node = self._path_list.get_path_node(path).data
            else:
                file_node = path
                path = file_node.name
            path = path.replace('/', '\\')
            p = os.path.join(save_path, path)
            if file_node.type:
                print(f'[*][download]{os.path.join(save_path, path)}')
                self.download_file(p, file_node.download_url)
            else:
                self.download(self._path_list.get_fid_list(file_node.id), p)

    def download_file(self, path, url):
        try:
            p = os.path.split(path)[0]
            os.makedirs(p)
            print(f'[+][mkdir]{p}')
        except FileExistsError:
            pass
        if os.path.exists(path):
            temp_size = os.path.getsize(path)
        else:
            temp_size = 0
        headers = {'Range': 'bytes=%d-' % temp_size}
        start_time = time.time()
        try:
            r = self._req.get(url, headers=headers, stream=True)
            file_size = int(r.headers['Content-Length'])
            if temp_size == file_size and file_size != 0:
                print(f'[+][download]{path}')
                return True
            elif temp_size > file_size:
                mode = 'wb'
            else:
                mode = 'ab'
            download_info = f'\r下载中... [{"*" * 10}] %0'
            show_download_info = download_info and file_size >= 1024 * 1024
            with open(path, mode) as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if show_download_info:
                        sys.stdout.write(download_info)
                    if chunk:
                        temp_size += len(chunk)
                        f.write(chunk)
                    total_time = time.time() - start_time
                    k = temp_size / file_size
                    download_info = f'\r下载中... [{"=" * int(k * 10)}{"*" * int((1 - k) * 10)}] %{math.ceil(k * 1000) / 10} {round(temp_size / total_time / 1024 / 1024, 2)}MB/s'
                if show_download_info:
                    print()
        except requests.exceptions.RequestException:
            print(f'[-][download]{path}')
            return False
        print(f'[+][download]{path}')
        return True

    def share(self, path, file_id):
        if path:
            file = self._path_list.get_path_node(path).data
        else:
            file = self._path_list.get_node_by_file_id(file_id).data
        print(file.download_url)
