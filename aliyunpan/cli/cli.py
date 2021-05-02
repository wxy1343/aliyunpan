import math
import os
import sys

import requests

from aliyunpan.api.core import AliyunPan
from aliyunpan.api.models import *
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
        self._share_link = 'aliyunpan://'
        self._txt = ''

    def init(self, config_file='~/.config/aliyunpan.yaml', refresh_token=None, username=None, password=None, depth=3):
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
        for i in self._path_list.get_path_list(path, update=False):
            if l:
                if i.type:
                    print(StrOfSize(i.size), time.strftime('%d %b %H:%M', i.ctime), i.id, i.name)
                else:
                    print('-', time.strftime('%d %b %H:%M', i.ctime), i.id, i.name)
            else:
                print(i.name, end='\t')

    def tree(self, path='root'):
        return self._path_list.tree(path)

    def rm(self, path):
        file_id = self._path_list.get_path_fid(path, update=False)
        if not file_id:
            raise FileNotFoundError(path)
        file_id_ = self._disk.delete_file(file_id)
        if file_id_ == file_id:
            self._path_list._tree.remove_node(file_id)
            print(f'[-][rm]{path}')
        return file_id_

    def mv(self, path, target_path):
        file_id = self._path_list.get_path_fid(path, update=False)
        _ = self._disk.move_file(self._path_list.get_path_fid(path, update=False),
                                 self._path_list.get_path_fid(target_path, update=False))
        if _ and file_id:
            print(f'[+][mv]{path} -> {target_path}')
            self._path_list._tree.remove_node(file_id)
            self._path_list.update_path_list(Path(target_path) / path, is_fid=False)
        else:
            print(f'[-][mv]{path} -> {target_path}')
        return _

    def mkdir(self, path):
        file_id_list = []
        path = PurePosixPath(str(path).replace('\\', '/'))
        if str(path) == 'root':
            return file_id_list
        file_id = self._path_list.get_path_fid(path, update=False)
        if file_id and file_id != 'root':
            file_id_list.append((file_id, path))
            return file_id_list
        parent_file_id = self._path_list.get_path_fid(path.parent, update=False)
        if not parent_file_id:
            file_id_list.extend(self.mkdir(path.parent))
            parent_file_id, _ = file_id_list[-1]
        r = self._disk.create_file(path.name, parent_file_id)
        try:
            file_id = r.json()['file_id']
        except KeyError:
            logger.debug(r.json()['message'])
            return False
        if file_id:
            print(f'[+][mkdir]{path}')
            self._path_list._tree.create_node(tag=path.name, identifier=file_id, parent=parent_file_id)
            file_id_list.append((file_id, path))
        return file_id_list

    def upload(self, path, upload_path='root', timeout=10.0, retry=3, force=False, share=False):
        if isinstance(path, str):
            path_list = (path,)
        else:
            path_list = path
        result_list = []
        for path in path_list:
            if path:
                if self._share_link in path:
                    share_list = []
                    if share:
                        share_info = parse_share_url(path)
                        file = self._path_list.get_path_node(share_info.name, update=False)
                        if file and not file.data.type:
                            path = path.replace(share_info.name, share_info.name + str(int(time.time())))
                            share_info = parse_share_url(path)
                        if not self._path_list.get_path_fid(share_info.name, update=False):
                            self.upload_share(share_info)
                            self._path_list.update_path_list(depth=0)
                        for line in self.cat(share_info.name).split('\n'):
                            if line.startswith(self._share_link):
                                share_list.append(parse_share_url(line))
                        self.rm(share_info.name)
                    else:
                        share_list = parse_share_url(path)
                    return self.upload_share(share_list, upload_path, force)
                path = Path(path)
                if path.is_file():
                    if share:
                        share_list = []
                        with open(path, 'r', encoding='utf-8') as f:
                            while True:
                                line = f.readline()
                                if not line:
                                    break
                                if line.startswith(self._share_link):
                                    share_list.append(parse_share_url(line))
                        return self.upload_share(share_list, upload_path, force)
                    else:
                        file_id = self._disk.upload_file(self._path_list.get_path_fid(upload_path, update=False),
                                                         path, timeout, retry, force)
                        result_list.append(file_id)
                elif path.is_dir():
                    if upload_path == 'root':
                        upload_path = '/'
                    upload_path = Path(upload_path)
                    upload_file_list = self.upload_dir(path, upload_path, timeout, retry, force)
                    for file in upload_file_list:
                        result = self._disk.upload_file(self._path_list.get_path_fid(file[0], update=False),
                                                        *file[1])
                        result_list.append(result)
                else:
                    raise FileNotFoundError
        if len(result_list) == 1:
            result_list = result_list[0]
        return result_list

    def upload_dir(self, path, upload_path, timeout, retry, force):
        upload_path = upload_path / path.name
        if not self._path_list.get_path_fid(upload_path, update=False):
            self.mkdir(upload_path)
        upload_file_list = []
        for file in path.iterdir():
            if file.is_dir():
                upload_file_list.extend(self.upload_dir(file, upload_path, timeout, retry, force))
            else:
                upload_file_list.append([upload_path, (file, timeout, retry, force)])
        return upload_file_list

    def upload_share(self, share_info_list, upload_path='root', force=False):
        if not isinstance(share_info_list, list):
            share_info_list = [share_info_list]
        if upload_path == 'root':
            upload_path = ''
        folder_list = []
        file_list = []
        for share_info in share_info_list:
            file_id_list = self.mkdir(upload_path / share_info.path)
            if file_id_list:
                for file_id, path in file_id_list:
                    folder_list.append((file_id, upload_path / path))
        folder_list = tuple(set(folder_list))
        for share_info in share_info_list:
            path = share_info.path
            if not str(upload_path) and str(path) == 'root':
                path = Path('')
            parent_file_id = self._path_list.get_path_fid(upload_path / path)
            result = self._disk.save_share_link(share_info.name, share_info.content_hash, share_info.content_hash_name,
                                                share_info.size, parent_file_id, force)
            p = PurePosixPath(str(upload_path / path / share_info.name).replace('\\', '/'))
            file_list.append((result, p))
            if result:
                print(f'[+]{p} 快速上传成功')
            else:
                print(f'[-]{p}')
        return folder_list, file_list

    def download(self, path, save_path, single_file=False, share=False):
        if not save_path:
            save_path = Path().cwd()
        save_path = Path(save_path)
        if isinstance(path, str):
            path_list = (path,)
        else:
            path_list = path
        for path in path_list:
            if str(path).startswith(self._share_link) or share:
                folder_list, file_list = self.upload(path, share=share)
                folder_list = sorted(folder_list, key=lambda x: x[1])
                for file_id, path in folder_list:
                    p = save_path / path
                    try:
                        p.mkdir(parents=True)
                        print(f'[+][mkdir]{p}')
                    except FileExistsError:
                        pass
                for file_id, path in file_list:
                    self.download_file(save_path / path, self._disk.get_download_url(file_id))
                for file_id, path in file_list:
                    try:
                        self.rm(path)
                    except FileNotFoundError:
                        pass
                for file_id, path in folder_list:
                    try:
                        self.rm(path)
                    except FileNotFoundError:
                        pass
                continue
            if isinstance(path, (Path, PurePosixPath, str)):
                path = PurePosixPath(str(path).replace('\\', '/'))
                node = self._path_list.get_path_node(path, update=False)
                if not node:
                    raise FileNotFoundError(path)
                file_node = node.data
                self._path_list.update_path_list(file_node.id)
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

    def cat(self, path, encoding='utf-8'):
        file_node = self._path_list.get_path_node(path, update=False)
        if not file_node:
            raise FileNotFoundError(path)
        file = file_node.data
        self._path_list.update_path_list(file.id)
        r = self._req.get(file.download_url)
        r.encoding = encoding
        return r.text

    def share(self, path, file_id, expire_sec, share_link, download_link, save):
        def share_(path, file_id, parent_file=''):
            if path:
                file_node = self._path_list.get_path_node(path, update=False)
                if not file_node:
                    raise FileNotFoundError(path)
                file = file_node.data
                self._path_list.update_path_list(file.id)
            else:
                file = self._path_list._tree.get_node(file_id).data
            if file.type:
                share_txt = file.name.center(50, '-') + '\n'
                if download_link:
                    share_txt += '下载链接'.center(50, '*') + '\n'
                    url = self._disk.get_download_url(file.id, expire_sec)
                    share_txt += url + '\n\n'
                if share_link:
                    share_txt += '分享链接'.center(50, '*') + '\n'
                    url = f'{self._share_link}{file.name}|{file.content_hash}|{file.size}|{parent_file or "root"}'
                    share_txt += url + '\n'
                    share_txt += '导入链接'.center(50, '*') + '\n'
                    share_txt += f'python main.py upload "{url}"' + '\n\n'
                print(share_txt)
                self._txt += share_txt
            else:
                for i in self._path_list.get_fid_list(file.id):
                    share_(path=None, file_id=i.id, parent_file=Path(parent_file) / file.name)

        self._txt += '*' * 50 + '\n'
        self._txt += '项目地址: https://github.com/wxy1343/aliyunpan' + '\n'
        self._txt += '*' * 50 + '\n\n'
        share_(path, file_id)
        if save:
            file_name = Path(path).name + f'{int(time.time())}.txt'
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(self._txt)
            print('文件导入'.center(50, '*'))
            print(f'python main.py upload -s {file_name}')
            print('链接导入'.center(50, '*'))
            file_id = self.upload(file_name)
            print()
            if file_id:
                self._path_list.update_path_list(depth=1)
                file = self._path_list._tree.get_node(file_id).data
                url = f'{self._share_link}{Path(path).name}|{file.content_hash}|{file.size}|root'
                print(f'python main.py upload -s "{url}"')
