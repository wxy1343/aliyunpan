import functools
import os
import platform
import re
import shutil
from typing import List, Union

import aria2p
import requests
from aria2p import Options

from aliyunpan.api.core import AliyunPan
from aliyunpan.api.models import *
from aliyunpan.api.req import *
from aliyunpan.api.type import Share, File
from aliyunpan.api.utils import *
from aliyunpan.cli.config import Config
from aliyunpan.common import *
from aliyunpan.exceptions import InvalidRefreshToken, InvalidPassword, InvalidConfiguration, \
    ConfigurationFileNotFoundError, AliyunpanCode, CreateDirError

__all__ = ['Commander']


class Commander:
    def __init__(self, init=True, *args, **kwargs):
        self.match = False
        self.whitelist = False
        self._disk = AliyunPan()
        self._path_list = PathList(self._disk)
        self._req = Req(self._disk)
        self._config = Config()
        self._task_config = Config(ROOT_DIR / Path('tasks.yaml'))
        self._share_link = 'aliyunpan://'
        self._print = Printer()
        self._host_url = 'https://www.aliyundrive.com/'
        self._aria2 = None
        self.filter_set = set()
        self._config_set = {'~/.config/aliyunpan.yaml', '.config/aliyunpan.yaml', '~/aliyunpan.yaml', 'aliyunpan.yaml',
                            os.environ.get('ALIYUNPAN_CONF', '')}
        GLOBAL_VAR.tasks = self._task_config.read()
        GLOBAL_VAR.txt = ''
        if init:
            self.init(*args, **kwargs)

    def __del__(self):
        self._task_config.write(GLOBAL_VAR.tasks)
        if self._disk.refresh_token:
            try:
                self._config.update('refresh_token', self._disk.refresh_token)
            except AttributeError:
                pass

    def init(self, config_file=None, refresh_token=None, username=None, password=None, depth=3, timeout=None,
             drive_id=None, album=False, share_id='', share_pwd='', filter_file=None, whitelist=False, match=False):
        self._path_list.depth = depth
        self._req.timeout = timeout
        self._disk.drive_id = drive_id
        self._disk.album = album
        self._disk._share = Share(share_id, share_pwd)
        self.filter_set.update(filter_file) if filter_file else None
        self.whitelist = whitelist
        self.match = match
        config_file_list = list(
            filter(lambda x: get_real_path(x).is_file(), map(lambda x: get_real_path(x), self._config_set)))
        if config_file:
            if not get_real_path(config_file).is_file():
                raise ConfigurationFileNotFoundError
            self._config = Config(get_real_path(config_file))
        elif config_file_list and config_file_list[0]:
            self._config = Config(config_file_list[0])
        if self._config.config_file and self._config.get('aria2'):
            aria2 = self._config.get('aria2')
        else:
            aria2 = {'host': 'http://localhost', 'port': 6800}
        if aria2:
            self._aria2 = self.aria2_init(**aria2)
        if refresh_token:
            if not len(refresh_token) == 32:
                raise InvalidRefreshToken
            self._disk.refresh_token = refresh_token
        elif username:
            if not password:
                raise InvalidPassword
            self._disk.login(username, password)
        elif self._config.config_file:
            refresh_token = self._config.get('refresh_token')
            username = self._config.get('username')
            password = self._config.get('password')
            if refresh_token:
                if not len(refresh_token) == 32:
                    raise InvalidRefreshToken
                self._disk.refresh_token = refresh_token
            elif username:
                if not password:
                    raise InvalidPassword
                self._disk.login(username, password)
            else:
                raise InvalidConfiguration
        else:
            raise ConfigurationFileNotFoundError

    def aria2_init(self, **kwargs):
        kwargs.setdefault('host', 'http://localhost')
        kwargs.setdefault('port', 6800)
        kwargs.setdefault('secret', '')
        self._aria2 = aria2p.API(
            aria2p.Client(
                **kwargs
            )
        )
        return self._aria2

    def ls(self, path='root', l=False, query=None):
        if query:
            file_info_list = self._path_list.get_file_info(self._disk.search(query))
        else:
            file_info_list = self._path_list.get_path_list(path, update=False)
        if self.filter_set:
            file_info_list = [i for i in file_info_list if self.file_filter(i.name)]
        for i, j in enumerate(file_info_list):
            if l:
                if j.type:
                    print(str_of_size(j.size), time.strftime('%d %b %H:%M', j.ctime), j.id, j.name, end='')
                else:
                    print('-', time.strftime('%d %b %H:%M', j.ctime), j.id, j.name, end='')
                if i + 1 < len(file_info_list):
                    print()
            else:
                print(j.name, end='\t')
        if platform.system() != 'Windows':
            print()

    def get_path_list(self, path='root') -> List[FileInfo]:
        return self._path_list.get_path_list(path, update=False)

    def get_fid_list(self, file_id='root') -> List[FileInfo]:
        return self._path_list.get_fid_list(file_id, update=False)

    def tree(self, path='root', stdout=sys.stdout):
        return self._path_list.tree(path, stdout)

    def rm(self, path, file_id=None):
        if not self.file_filter(path):
            return False
        if not file_id:
            file_id = self._path_list.get_path_fid(path, update=False)
        if file_id:
            file_id_ = self._disk.delete_file(file_id)
            if file_id_ == file_id:
                file_id = file_id_
                self._print.remove_info(path or file_id, status=True)
                self._path_list._tree.remove_node(file_id)
                self._print.print_line()
            else:
                file_id = False
                self._print.remove_info(path or file_id, status=False)
                self._print.print_line()
        else:
            raise FileNotFoundError(path or file_id)
        return file_id

    def rename(self, path, name):
        if not self.file_filter(path):
            return False
        file_id = self._path_list.get_path_fid(path, update=False)
        status = False
        existed = False
        if file_id:
            file_id_ = self._disk.update_file(file_id, name)
            if file_id_ == AliyunpanCode.existed:
                file_id = False
                existed = True
            elif file_id_ == file_id:
                file_id = file_id_
                self._path_list.update_path_list(file_id=self._path_list._tree.get_node(file_id).data.pid, depth=0)
                status = True
        else:
            status = False
        self._print.rename_info(path, name=name, status=status, existed=existed)
        return file_id

    def move_by_path_list(self, path_list, target_path) -> List[File]:
        target_path = AliyunpanPath(target_path)
        parent_file_id = self._path_list.get_path_fid(target_path, update=False)
        parent_file_node = self._path_list._tree.get_node(parent_file_id)
        file_list = []
        file_list_ = []
        for path in path_list:
            path = AliyunpanPath(path)
            if not self.file_filter(path):
                continue
            if parent_file_id and parent_file_node:
                if parent_file_node.data.type:
                    raise FileExistsError(target_path)
                if self._disk._share and path in ('', '/', '\\', '.', 'root', '..'):
                    file_list.extend(self.move_share_file(path, target_path))
                    continue
                file_id = self._path_list.get_path_fid(path, update=False)
                file_list.append(File(file_id, path))
                if file_id:
                    file_list_.append(File(file_id, path))
            elif path.parent == target_path.parent:
                file_id = self.rename(path, target_path.name)
                file_list.append(File(file_id, path))
                self._print.print_line()
                continue
            elif not parent_file_id:
                raise FileNotFoundError(target_path)
        file_list.extend(self.move_by_file_id_list(file_list_, parent_file_id))
        if file_list_:
            for file in file_list_:
                if file:
                    if file.file_id:
                        self._print.move_info(file.path, target_path, status=True)
                        self._path_list._tree.remove_node(file.file_id)
                        self._path_list.update_path_list(Path(target_path) / file.path.name, is_fid=False)
                    else:
                        self._print.move_info(file.path, target_path, status=False)
                    self._print.print_line()
        return file_list

    def move_by_path(self, path, target_path):
        return self.move_by_path_list([path], target_path)

    def move_by_file_id_list(self, file_list, parent_file_id):
        return self._disk.move_file(file_list, parent_file_id)

    def move_share_file(self, path: str, target_path: AliyunpanPath) -> List[File]:
        parent_file_id = 'root'
        if path == '..':
            target_path = target_path / self._disk._share.share_id
            file_list = self.mkdir(target_path)
            if not file_list:
                raise CreateDirError
            parent_file_id = file_list[0].file_id
        path_list = self.get_path_list()
        file_list = self._disk.move_file([File(i.id, target_path / i.name) for i in path_list],
                                         parent_file_id)
        for file in file_list:
            for path in path_list:
                if file.file_id == path.id:
                    self._print.move_info(path.name, target_path, status=True)
                    self._path_list.update_path_list(path.name, is_fid=False)
                    self._print.print_line()
        return file_list

    def mv(self, path, target_path) -> List[File]:
        return self.move_by_path(path, target_path)

    def mkdir(self, path, name=None, parent_file_id=None) -> List[File]:
        file_list: List[File] = []
        if not self.file_filter(path):
            return []
        if not parent_file_id or not name:
            path = AliyunpanPath(path)
            name = path.name
            if str(path) == 'root':
                return file_list
            file_id = self._path_list.get_path_fid(path, update=False)
            if file_id and file_id != 'root':
                return file_list
            parent_file_id = self._path_list.get_path_fid(path.parent, update=False)
            if not parent_file_id:
                file_list.extend(self.mkdir(path.parent))
                parent_file_id, _ = file_list[-1]
        r = self._disk.create_file(name, parent_file_id)
        try:
            file_id = r.json()['file_id']
        except KeyError:
            logger.debug(r.json()['message'])
            return []
        if file_id:
            self._print.mkdir_info(path, status=True)
            self._print.print_line()
            self._path_list._tree.create_node(tag=name, identifier=file_id, parent=parent_file_id,
                                              data=FileInfo(name=name, type=False, id=file_id, pid=parent_file_id))
            file_list.append(File(file_id, path))
        return file_list

    def file_filter(self, path, whitelist=None):
        if not path:
            return False
        if whitelist is None:
            whitelist = self.whitelist
        if isinstance(path, FileInfo):
            name = path.name
        else:
            name = Path(path)
        for pattern in self.filter_set:
            if re.match(pattern, str(name)):
                return whitelist
        return not whitelist

    def upload(self, path, upload_path='root', timeout=10.0, retry=3, force=False, share=False, chunk_size=None,
               c=False, ignore=False):
        if isinstance(path, (str, AliyunpanPath, Path)):
            path_list = {path}
        else:
            path_list = path
        if self.match:
            [self.filter_set.add(i) for i in path_list]
            if self.whitelist:
                path_list = set(filter(functools.partial(self.file_filter, whitelist=False), Path().iterdir()))
            else:
                path_list = set(filter(functools.partial(self.file_filter, whitelist=True), Path().iterdir()))
        else:
            path_list = filter(self.file_filter, path_list)
        result_list = []
        for path in path_list:
            path: Union[str, AliyunpanPath, Path]
            if self._share_link in str(path):
                share_list = []
                if share:
                    share_info = parse_share_url(path, self._disk.access_token)
                    file = self._path_list.get_path_node(share_info.name, update=False)
                    if file and not file.data.type:
                        path = f'{self._share_link}{path.lstrip(self._share_link).split("|")[0]}_{str(int(time.time()))}|{path.split("|", 1)[1]}'
                        share_info = parse_share_url(path, self._disk.access_token)
                    if not self._path_list.get_path_fid(share_info.name, update=False):
                        self.upload_share(share_info)
                        self._path_list.update_path_list(depth=0)
                    if str(share_info.path) == 'root':
                        path_ = share_info.name
                    else:
                        path_ = share_info.path / share_info.name
                    for line in self.cat(path_).split('\n'):
                        if line.startswith(self._share_link):
                            share_list.append(parse_share_url(line, self._disk.access_token))
                    self.rm(path_)
                    if str(upload_path) == 'root':
                        upload_path = share_info.path
                    else:
                        upload_path /= share_info.path
                else:
                    share_list = parse_share_url(path, self._disk.access_token)
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
                                share_list.append(parse_share_url(line, self._disk.access_token))
                    return self.upload_share(share_list, upload_path, force)
                else:
                    parent_file_id = self._path_list.get_path_fid(upload_path, update=False)
                    if not parent_file_id:
                        raise FileNotFoundError(upload_path)
                    try:
                        result = self._disk.upload_file(
                            parent_file_id=parent_file_id, path=str(path),
                            upload_timeout=timeout, retry_num=retry, force=force, chunk_size=chunk_size, c=c,
                            ignore=ignore)
                    except KeyboardInterrupt:
                        self.__del__()
                        raise
                    if result:
                        if isinstance(result, str):
                            file_id = result
                        else:
                            file_info = self._path_list.get_file_info(result)[0]
                            file_id = file_info.id
                            self._path_list._tree.create_node(tag=file_info.name, identifier=file_info.id,
                                                              parent=parent_file_id, data=file_info)
                        result_list.append(file_id)
            elif path.is_dir():
                if upload_path == 'root':
                    upload_path = '/'
                upload_path = Path(upload_path)
                upload_file_list = self.upload_dir(path, upload_path)
                upload_file_list = [i for i in upload_file_list if self.file_filter(i[1])]
                for file in upload_file_list:
                    try:
                        parent_file_id = self._path_list.get_path_fid(file[0], update=False)
                        if not parent_file_id:
                            raise FileNotFoundError(upload_path)
                        result = self._disk.upload_file(
                            parent_file_id=parent_file_id, path=file[1],
                            upload_timeout=timeout, retry_num=retry, force=force, chunk_size=chunk_size, c=c,
                            ignore=ignore)
                    except KeyboardInterrupt:
                        self.__del__()
                        raise
                    if result:
                        if isinstance(result, str):
                            file_id = result
                        else:
                            file_info = self._path_list.get_file_info(result)[0]
                            file_id = file_info.id
                            self._path_list._tree.create_node(tag=file_info.name, identifier=file_info.id,
                                                              parent=parent_file_id, data=file_info)
                        result_list.append(file_id)
            else:
                raise FileNotFoundError
            for file_hash, path in GLOBAL_VAR.file_set:
                if file_hash in GLOBAL_VAR.tasks and GLOBAL_VAR.tasks[file_hash].upload_time:
                    if isinstance(GLOBAL_VAR.tasks[file_hash].path, str):
                        del GLOBAL_VAR.tasks[file_hash]
                    else:
                        try:
                            GLOBAL_VAR.tasks[file_hash].path.remove(path)
                        except ValueError:
                            pass
                        if not GLOBAL_VAR.tasks[file_hash].path:
                            del GLOBAL_VAR.tasks[file_hash]
        return result_list

    def upload_dir(self, path, upload_path):
        upload_path = upload_path / path.name
        if not self._path_list.get_path_fid(upload_path, update=False):
            self.mkdir(upload_path)
            self._print.print_line()
        upload_file_list = []
        for file in path.iterdir():
            if file.is_dir():
                upload_file_list.extend(self.upload_dir(file, upload_path))
            else:
                upload_file_list.append([upload_path, file])
        return upload_file_list

    def upload_share(self, share_info_list: List[ShareInfo], upload_path='root', force=False):
        if not isinstance(share_info_list, list):
            share_info_list = [share_info_list]
        if upload_path == 'root':
            upload_path = ''
        upload_path = AliyunpanPath(upload_path)
        folder_list = []
        file_list = []
        for share_info in share_info_list:
            path = share_info.path
            if str(upload_path) in ('', '.') and str(path) == 'root':
                path = Path('')
            if str(upload_path) == 'root':
                upload_path = AliyunpanPath()
            p = upload_path / path
            if str(p) not in ('', '.'):
                file_list = self.mkdir(upload_path / path)
            if file_list:
                for file_id, path in file_list:
                    folder_list.append((file_id, upload_path / path))
        folder_list = list(set(folder_list))
        file_list = []
        for share_info in share_info_list:
            share_info: ShareInfo
            path = share_info.path
            if str(upload_path) in ('', '.') and str(path) == 'root':
                path = Path()
            parent_file_id = self._path_list.get_path_fid(upload_path / path)
            result = self._disk.save_share_link(share_info.name, share_info.content_hash, share_info.proof_code,
                                                share_info.content_hash_name, share_info.size, parent_file_id, force)
            p = AliyunpanPath(upload_path / path / share_info.name)
            file_list.append(File(result, p))
            self._print.print_line()
            if result:
                self._print.upload_info(p, status=True, rapid_upload=True)
            else:
                self._print.upload_info(p, status=False)
        return folder_list, file_list

    def download(self, path, save_path=None, single_file=False, share=False, chunk_size=None, aria2=False,
                 first=True, **kwargs):
        if not chunk_size:
            chunk_size = 1048576
        if not save_path:
            save_path = Path().cwd()
        save_path = Path(save_path)
        if isinstance(path, str):
            path_list = {path}
        else:
            path_list = path
        if not first:
            path_list = [i for i in path_list if self.file_filter(i)]
        kwargs.setdefault('referer', self._host_url)
        for path in path_list:
            if str(path).startswith(self._share_link) or share:
                folder_list, file_list = self.upload(path, share=share)
                folder_list = sorted(folder_list, key=lambda x: x[1])
                for file_id, path in folder_list:
                    p = save_path / path
                    try:
                        if not aria2:
                            p.mkdir(parents=True)
                            self._print.mkdir_info(p, status=True)
                    except FileExistsError:
                        pass
                for file_id, path in file_list:
                    if aria2:
                        kwargs.update({'dir': str((save_path / path).parent.absolute()), 'out': path.name})
                        self._aria2.add_uris([self._disk.get_download_url(file_id)], Options(self._aria2, kwargs))
                    else:
                        self.download_file(save_path / path, self._disk.get_download_url(file_id), chunk_size)
                for file_id, path in file_list:
                    self._path_list.update_path_list(path.parent, depth=0, is_fid=False)
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
            if isinstance(path, (Path, PurePosixPath, AliyunpanPath, str)):
                path = AliyunpanPath(path)
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
                if aria2:
                    kwargs.update({'dir': str(p.parent.absolute()), 'out': p.name})
                    self._aria2.add_uris([self._disk.get_download_url(file_node.id)], Options(self._aria2, kwargs))
                    self._print.download_info(p, status=True, aria2=True)
                else:
                    self._print.download_info(p)
                    self._print.print_line()
                    self._path_list.update_path_list(file_node.id)
                    self.download_file(p, file_node.download_url, chunk_size)
                self._print.print_line()
            else:
                self.download(self._path_list.get_fid_list(file_node.id), save_path=save_path / p.name,
                              chunk_size=chunk_size, aria2=aria2, first=False, **kwargs)

    def download_file(self, path, url, chunk_size=1048576):
        if not self.file_filter(path):
            return False
        try:
            path.parent.mkdir(parents=True)
            self._print.print_line()
            self._print.mkdir_info(path.parent, status=True)
            self._print.print_line()
        except FileExistsError:
            pass
        if path.exists():
            temp_size = path.stat().st_size
        else:
            temp_size = 0
        headers = {'Range': 'bytes=%d-' % temp_size}
        try:
            r = self._req.get(url, headers=headers, stream=True)
            file_size = int(r.headers['Content-Length'])
            if temp_size == file_size and file_size != 0:
                self._print.print_line()
                self._print.download_info(path, status=True)
                return True
            elif temp_size > file_size:
                mode = 'wb'
                temp_size = 0
            else:
                mode = 'ab'
            self._print.print_line()
            download_bar = DownloadBar(size=file_size)
            download_bar.update(refresh_line=False)
            with path.open(mode) as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    k = temp_size / file_size
                    download_bar.update(ratio=k, refresh_line=True)
                    if chunk:
                        temp_size += len(chunk)
                        f.write(chunk)
        except requests.exceptions.RequestException:
            self._print.refresh_line()
            self._print.download_info(path, status=False)
            self._print.print_line()
            return False
        self._print.download_info(path, status=True, t=download_bar.time, average_speed=download_bar.average_speed,
                                  refresh_line=True)
        self._print.print_line()
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

    def share(self, path, expire_sec, share_link, download_link, save):
        if not self.file_filter(path):
            return False

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
                url = self._disk.get_download_url(file.id, expire_sec, file.category)
                if download_link:
                    share_txt += '下载链接'.center(50, '*') + '\n'
                    share_txt += url + '\n\n'
                if share_link:
                    share_txt += '分享链接'.center(50, '*') + '\n'
                    url_base64 = base64.b64encode(url.encode()).decode()
                    url = f'{self._share_link}{file.name}|{file.content_hash}|{url_base64}|{file.size}|{parent_file or "root"}'
                    share_txt += url + '\n'
                    share_txt += '导入链接'.center(50, '*') + '\n'
                    share_txt += f'python aliyunpan.py upload "{url}"' + '\n\n'
                print(share_txt)
                GLOBAL_VAR.txt += share_txt
            else:
                for i in self._path_list.get_fid_list(file.id):
                    share_(path=None, file_id=i.id, parent_file=Path(parent_file) / file.name)

        GLOBAL_VAR.txt += '*' * 50 + '\n'
        GLOBAL_VAR.txt += '项目地址: https://github.com/wxy1343/aliyunpan' + '\n'
        GLOBAL_VAR.txt += '*' * 50 + '\n\n'
        if expire_sec is None:
            expire_sec = 14400
        share_(path, file_id=None)
        if save:
            file_name = Path(path).name + f'{int(time.time())}.txt'
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(GLOBAL_VAR.txt)
            print('文件导入'.center(50, '*'))
            print(f'python aliyunpan.py upload -s {file_name}')
            print('链接导入'.center(50, '*'))
            file_id = self.upload(file_name)[0]
            print()
            if file_id:
                self._path_list.update_path_list(depth=0)
                file = self._path_list._tree.get_node(file_id).data
                url_base64 = base64.b64encode(self.disk.get_download_url(file_id).encode()).decode()
                url = f'{self._share_link}{Path(path).name}|{file.content_hash}|{url_base64}|{file.size}|root'
                print(f'python aliyunpan.py upload -s "{url}"')

    def tui(self):
        from aliyunpan.cli.tui import AliyunpanTUI
        aliyunpan_tui = AliyunpanTUI(self)
        aliyunpan_tui.run()

    def sync(self, path, upload_path, sync_time, time_out, chunk_size, retry, delete, first=True):
        if first and path == 'root':
            self._print.print_info(
                'Do you really want to synchronize the root? This operation may delete all your files.', error=True)
            input('\nEnter to continue.')
        path = AliyunpanPath(path)
        relative_path = AliyunpanPath(path.name)
        if str(relative_path) == '.':
            return self.sync(path.absolute(), upload_path, sync_time, time_out, chunk_size, retry, delete,
                             first=False)
        upload_path = AliyunpanPath(upload_path)
        p = upload_path / relative_path
        self._path_list.update_path_list(p, is_fid=False)
        file_id = self._path_list.get_path_fid(p, update=False)
        if not file_id:
            self.upload(path, upload_path, timeout=time_out, chunk_size=chunk_size, retry=retry)
            self._path_list.update_path_list(p, is_fid=False)
            file_id = self._path_list.get_path_fid(p, update=False)
        path_ = self._path_list._tree.to_dict(file_id, with_data=True)[str(relative_path)]
        change_file_list = self._path_list.check_path_diff(path, path_['children'] if 'children' in path_ else [])
        change_file_list = filter(self.file_filter, change_file_list)
        for path_ in change_file_list:
            relative_path = path.name / (path - path_)
            if path_.exists():
                if not self.upload(path_, upload_path / relative_path.parent, force=True, timeout=time_out,
                                   chunk_size=chunk_size, retry=retry, ignore=True):
                    if first:
                        self._print.upload_info(path_, status=False)
                        self._print.print_line()
            elif delete:
                self.rm(upload_path / relative_path)
        if sync_time:
            self._print.wait_info('等待{time}秒后再次同步', t=sync_time, refresh_line=True)
            self._print.refresh_line()
            self.sync(path, upload_path, sync_time, time_out, chunk_size, retry, delete=delete, first=False)

    def sync_local(self, sync_path, save_path, sync_time, chunk_size, delete, **kwargs):
        if not save_path:
            save_path = '.'
        path = AliyunpanPath(save_path) + AliyunpanPath(sync_path).name
        if not path.exists():
            self.download(sync_path, save_path)
        file_id = self.path_list.get_path_fid(sync_path, update=False)
        if not file_id:
            raise FileNotFoundError(sync_path)
        self._path_list.update_path_list(sync_path, is_fid=False)
        path_ = self._path_list._tree.to_dict(file_id, with_data=True)[str(AliyunpanPath(sync_path)).name]
        change_file_list = self._path_list.check_path_diff(path, path_['children'] if 'children' in path_ else [])
        for path_ in change_file_list:
            p = str(AliyunpanPath(path_) - AliyunpanPath(save_path))
            file_node = self.path_list.get_path_node(p)
            if not file_node:
                if delete:
                    Path(path_).unlink() if path_.is_file() else shutil.rmtree(path_)
                    self._print.remove_info(path_, True)
                    self._print.print_line()
            else:
                self.download(p, str(save_path / Path(p).parent), chunk_size=chunk_size, **kwargs)
        if sync_time:
            self._print.wait_info('等待{time}秒后再次同步', t=sync_time, refresh_line=True)
            self._print.refresh_line()
            return self.sync_local(sync_path, save_path, sync_time=sync_time, chunk_size=chunk_size, delete=delete,
                                   **kwargs)

    def share_link(self, path_list, file_id_list=None, expiration=None):
        path_list = filter(self.file_filter, path_list)
        t = '' if expiration is None else time.time() + expiration
        if not file_id_list:
            file_id_list = [self._path_list.get_path_fid(path, update=False) for path in path_list]
        file_id_list = list(filter(None, file_id_list))
        if file_id_list:
            print(self._disk.share_link(file_id_list, t))
        else:
            raise FileNotFoundError

    def auto_refresh_token(self, refresh_time):
        print('Start to refresh token automatically.')
        while True:
            time.sleep(refresh_time)
            self._disk.token_refresh()
            print(time.strftime("%Y-%m-%d %H:%M:%S: ", time.localtime()) + self.disk.refresh_token)

    @property
    def req(self):
        return self._req

    @property
    def config(self):
        return self._config

    @property
    def path_list(self):
        return self._path_list

    @property
    def disk(self):
        return self._disk
