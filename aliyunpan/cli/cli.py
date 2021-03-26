import os
import time

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

    def upload_dir(self, path, upload_path, timeout, retry, force):
        print(os.path.join(upload_path, os.path.split(path)[1]).replace('\\', '/'))
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
            if path:
                file_list = self._path_list.get_path_list(path)
                if file_list:
                    for file in file_list:
                        if file.download_url:
                            p = os.path.join(save_path, path.lstrip('/'))
                            if os.path.exists(p):
                                temp_size = os.path.getsize(p)
                            else:
                                temp_size = 0
                            headers = {'Range': 'bytes=%d-' % temp_size}
                            r = self._req.get(file.download_url, headers=headers, stream=True)
                            f = os.path.join(path, file.name).replace("\\", "/")
                            print(f'download {f} to {p}')
                            with open(p, 'ab') as f:
                                for chunk in r.iter_content(chunk_size=1024):
                                    if chunk:
                                        temp_size += len(chunk)
                                        f.write(chunk)
                            print(p, '下载成功')
                        elif not file.type:
                            p = os.path.join(save_path, path.lstrip('/'))
                            try:
                                os.makedirs(os.path.join(p, file.name))
                            except FileExistsError:
                                pass
                            d = os.path.join(path, file.name).replace('\\', '/')
                            print(f'mkdir {d}')
                            self.download([os.path.join(path, file.name).replace('\\', '/')],
                                          os.path.join(p, file.name))
