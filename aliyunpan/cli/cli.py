import math
import os
import sys
import time
from pathlib import Path

import requests

from aliyunpan.api.core import AliyunPan
from aliyunpan.api.models import PathList
from aliyunpan.api.req import *
from aliyunpan.api.utils import *
from aliyunpan.cli.config import Config

__all__ = ['Commander']


class Commander:
    def __init__(self):
        self._disk = AliyunPan()
        self._path_list = PathList(self._disk)
        self._req = Req()
        self._config = Config()

    def init(self, config_file='', refresh_token=None, username=None, password=None, depth=3):
        self._path_list.depth = depth
        spectify_conf_file = os.environ.get("ALIYUNPAN_CONF", "")
        config_file = list(
            filter(lambda x: Path(x).is_file(), map(lambda x: Path(x).expanduser(), [spectify_conf_file, config_file])))
        if refresh_token:
            if not len(refresh_token) == 32:
                raise Exception('Is not a valid refresh_token')
            self._disk.refresh_token = refresh_token
        elif username:
            if not password:
                raise Exception('Password not found.')
            self._disk.login(username, password)
        elif config_file:
            self._config.config_file = config_file[0]
            refresh_token = self._config.get('refresh_token')
            username = self._config.get('username')
            password = self._config.get('password')
            if refresh_token:
                if not len(refresh_token) == 32:
                    raise Exception('Is not a valid refresh_token')
                self._disk.refresh_token = refresh_token
            elif username:
                if not password:
                    raise Exception('Password not found.')
                self._disk.login(username, password)
            else:
                raise Exception('Configuration file error.')

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

    def tree(self, path='root'):
        return self._path_list.tree(path)

    def rm(self, path, update=False):
        file_id = self._path_list.get_path_fid(path)
        _ = self._disk.delete_file(file_id)
        if _ and file_id and update:
            self._path_list._tree.remove_node(file_id)
        return _

    def mv(self, path, target_path, update=False):
        file_id = self._path_list.get_path_fid(path)
        _ = self._disk.move_file(self._path_list.get_path_fid(path), self._path_list.get_path_fid(target_path))
        if update:
            if _ and file_id:
                self._path_list._tree.remove_node(file_id)
            self._path_list.update_path_list(target_path, is_fid=False)
        return _

    def mkdir(self, path, update=False):
        path = Path(path)
        file_id = self._path_list.get_path_fid(path)
        if file_id:
            return True
        parent_file_id = self._path_list.get_path_fid(path.parent)
        r = self._disk.create_file(path.name, parent_file_id)
        try:
            file_id = r.json()['file_id']
        except KeyError:
            logger.debug(r.json()['message'])
            return False
        if file_id:
            print(f'[+][mkdir]{path}')
            if update:
                self._path_list.update_path_list(path.parent, is_fid=False)
            else:
                self._path_list._tree.create_node(tag=path.name, identifier=file_id, parent=parent_file_id)
        return file_id

    def upload(self, path, upload_path='root', timeout=10.0, retry=3, force=False):
        if isinstance(path, str):
            path_list = (path,)
        else:
            path_list = path
        for path in path_list:
            if path:
                path = Path(path)
                if path.is_file():
                    self._disk.upload_file(self._path_list.get_path_fid(upload_path), path, timeout, retry, force)
                elif path.is_dir():
                    if upload_path == 'root':
                        upload_path = '/'
                    upload_path = Path(upload_path)
                    upload_file_list = self.upload_dir(path, upload_path, timeout, retry, force)
                    self._path_list.update_path_list(upload_path, is_fid=False)
                    for file in upload_file_list:
                        self._disk.upload_file(self._path_list.get_path_fid(file[0]), *file[1])
                else:
                    raise FileNotFoundError

    def upload_dir(self, path, upload_path, timeout, retry, force):
        upload_path = upload_path / path.name
        if not self._path_list.get_path_fid(upload_path):
            self.mkdir(upload_path)
        upload_file_list = []
        for file in path.iterdir():
            if file.is_dir():
                upload_file_list.extend(self.upload_dir(file, upload_path, timeout, retry, force))
            else:
                upload_file_list.append([upload_path, (file, timeout, retry, force)])
        return upload_file_list

    def download(self, path, save_path, single_file=False):
        if save_path == '':
            save_path = Path().cwd()
        save_path = Path(save_path)
        if isinstance(path, str):
            path_list = (path,)
        else:
            path_list = path
        for path in path_list:
            if isinstance(path, (Path, str)):
                path = Path(path)
                node = self._path_list.get_path_node(path)
                if not node:
                    raise FileNotFoundError(path)
                file_node = node.data
                if file_node.type:
                    single_file = True
            else:
                file_node, path = path, path.name
            p = save_path / path
            if file_node.type:
                if single_file:
                    p = save_path / p.name
                print(f'[*][download]{p}')
                self.download_file(p, file_node.download_url)
            else:
                self.download(self._path_list.get_fid_list(file_node.id), save_path / p.name)

    def download_file(self, path, url):
        try:
            path.parent.mkdir(parents=True)
            print(f'[+][mkdir]{path.parent}')
        except FileExistsError:
            pass
        if path.exists():
            temp_size = path.stat().st_size
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
                temp_size = 0
            else:
                mode = 'ab'
            download_info = f'\r下载中... [{"*" * 10}] %0'
            show_download_info = download_info and file_size >= 1024 * 1024
            with path.open(mode) as f:
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

    def share(self, path, file_id, expire_sec):
        if path:
            file = self._path_list.get_path_node(path).data
        else:
            file = self._path_list._tree.get_node(file_id).data
        print(self._disk.get_download_url(file.id, expire_sec))
