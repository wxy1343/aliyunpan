import os

import requests

from aliyunpan.api.core import AliyunPan
from aliyunpan.api.models import *
from aliyunpan.api.req import *
from aliyunpan.api.utils import *
from aliyunpan.cli.config import Config
from aliyunpan.cli.tui import AliyunpanTUI
from aliyunpan.common import *
from aliyunpan.exceptions import InvalidRefreshToken, InvalidPassword, InvalidConfiguration, \
    ConfigurationFileNotFoundError, AliyunpanCode

__all__ = ['Commander']


class Commander:
    def __init__(self):
        self._disk = AliyunPan()
        self._path_list = PathList(self._disk)
        self._req = Req()
        self._config = Config()
        self._task_config = Config(ROOT_DIR / Path('tasks.yaml'))
        self._share_link = 'aliyunpan://'
        self._print = Printer()
        GLOBAL_VAR.tasks = self._task_config.read()
        GLOBAL_VAR.txt = ''

    def __del__(self):
        self._task_config.write(GLOBAL_VAR.tasks)

    def init(self, config_file='~/.config/aliyunpan.yaml', refresh_token=None, username=None, password=None, depth=3):
        self._path_list.depth = depth
        specify_conf_file = os.environ.get("ALIYUNPAN_CONF", "")
        config_file = list(
            filter(lambda x: Path(x).is_file(), map(lambda x: Path(x).expanduser(), [specify_conf_file, config_file])))
        if refresh_token:
            if not len(refresh_token) == 32:
                raise InvalidRefreshToken
            self._disk.refresh_token = refresh_token
        elif username:
            if not password:
                raise InvalidPassword
            self._disk.login(username, password)
        elif config_file:
            self._config.config_file = config_file[0]
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

    def ls(self, path, l, query=None):
        if query:
            file_info_list = self._path_list.get_file_info(self._disk.search(query))
        else:
            file_info_list = self._path_list.get_path_list(path, update=False)
        for i in file_info_list:
            if l:
                if i.type:
                    print(str_of_size(i.size), time.strftime('%d %b %H:%M', i.ctime), i.id, i.name)
                else:
                    print('-', time.strftime('%d %b %H:%M', i.ctime), i.id, i.name)
            else:
                print(i.name, end='\t')

    def tree(self, path='root'):
        return self._path_list.tree(path)

    def rm(self, path):
        file_id = self._path_list.get_path_fid(path, update=False)
        if file_id:
            file_id_ = self._disk.delete_file(file_id)
            if file_id_ == file_id:
                file_id = file_id_
                self._print.remove_info(path, status=False)
                self._path_list._tree.remove_node(file_id)
            else:
                file_id = False
        return file_id

    def rename(self, path, name):
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

    def mv(self, path, target_path):
        file_id = self._path_list.get_path_fid(path, update=False)
        _ = self._disk.move_file(self._path_list.get_path_fid(path, update=False),
                                 self._path_list.get_path_fid(target_path, update=False))
        if _ and file_id:
            self._print.move_info(path, target_path, status=True)
            self._path_list._tree.remove_node(file_id)
            self._path_list.update_path_list(Path(target_path) / path, is_fid=False)
        else:
            self._print.move_info(path, target_path, status=False)
        return _

    def mkdir(self, path):
        file_id_list = []
        path = PurePosixPath(Path(path).as_posix())
        if str(path) == 'root':
            return file_id_list
        file_id = self._path_list.get_path_fid(path, update=False)
        if file_id and file_id != 'root':
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
            self._print.mkdir_info(path, status=True)
            self._path_list._tree.create_node(tag=path.name, identifier=file_id, parent=parent_file_id)
            file_id_list.append((file_id, path))
        return file_id_list

    def upload(self, path, upload_path='root', timeout=10.0, retry=3, force=False, share=False, chunk_size=None,
               c=False):
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
                        if str(share_info.path) == 'root':
                            path_ = share_info.name
                        else:
                            path_ = share_info.path / share_info.name
                        for line in self.cat(path_).split('\n'):
                            if line.startswith(self._share_link):
                                share_list.append(parse_share_url(line))
                        self.rm(path_)
                        if str(upload_path) == 'root':
                            upload_path = share_info.path
                        else:
                            upload_path /= share_info.path
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
                        try:
                            file_id = self._disk.upload_file(
                                parent_file_id=self._path_list.get_path_fid(upload_path, update=False), path=path,
                                upload_timeout=timeout, retry_num=retry, force=force, chunk_size=chunk_size, c=c)
                        except KeyboardInterrupt:
                            self.__del__()
                            raise
                        result_list.append(file_id)
                elif path.is_dir():
                    if upload_path == 'root':
                        upload_path = '/'
                    upload_path = Path(upload_path)
                    upload_file_list = self.upload_dir(path, upload_path)
                    for file in upload_file_list:
                        try:
                            result = self._disk.upload_file(
                                parent_file_id=self._path_list.get_path_fid(file[0], update=False), path=file[1],
                                upload_timeout=timeout, retry_num=retry, force=force, chunk_size=chunk_size, c=c)
                        except KeyboardInterrupt:
                            self.__del__()
                            raise
                        result_list.append(result)
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
        if len(result_list) == 1:
            result_list = result_list[0]
        return result_list

    def upload_dir(self, path, upload_path):
        upload_path = upload_path / path.name
        if not self._path_list.get_path_fid(upload_path, update=False):
            self.mkdir(upload_path)
        upload_file_list = []
        for file in path.iterdir():
            if file.is_dir():
                upload_file_list.extend(self.upload_dir(file, upload_path))
            else:
                upload_file_list.append([upload_path, file])
        return upload_file_list

    def upload_share(self, share_info_list: ShareInfo, upload_path='root', force=False):
        if not isinstance(share_info_list, list):
            share_info_list = [share_info_list]
        if upload_path == 'root':
            upload_path = ''
        upload_path = PurePosixPath(Path(upload_path).as_posix())
        folder_list = []
        file_list = []
        file_id_list = None
        for share_info in share_info_list:
            path = share_info.path
            if str(upload_path) in ('', '.') and str(path) == 'root':
                path = Path('')
            if str(upload_path) == 'root':
                upload_path = PurePosixPath('')
            p = upload_path / path
            if str(p) not in ('', '.'):
                file_id_list = self.mkdir(upload_path / path)
            if file_id_list:
                for file_id, path in file_id_list:
                    folder_list.append((file_id, upload_path / path))
        folder_list = tuple(set(folder_list))
        for share_info in share_info_list:
            path = share_info.path
            if str(upload_path) in ('', '.') and str(path) == 'root':
                path = Path('')
            parent_file_id = self._path_list.get_path_fid(upload_path / path)
            result = self._disk.save_share_link(share_info.name, share_info.content_hash, share_info.content_hash_name,
                                                share_info.size, parent_file_id, force)
            p = PurePosixPath(Path(upload_path / path / share_info.name).as_posix())
            file_list.append((result, p))
            if result:
                self._print.upload_info(p, status=True, rapid_upload=True)
            else:
                self._print.upload_info(p, status=False)
        return folder_list, file_list

    def download(self, path, save_path=None, single_file=False, share=False, chunk_size=1048576):
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
                        self._print.mkdir_info(p, status=True)
                    except FileExistsError:
                        pass
                for file_id, path in file_list:
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
            if isinstance(path, (Path, PurePosixPath, str)):
                path = PurePosixPath(Path(path).as_posix())
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
                self._print.download_info(p)
                self.download_file(p, file_node.download_url, chunk_size)
            else:
                self.download(self._path_list.get_fid_list(file_node.id), save_path / p.name)

    def download_file(self, path, url, chunk_size=1048576):
        try:
            path.parent.mkdir(parents=True)
            self._print.mkdir_info(path.parent, status=True)
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
                self._print.download_info(path, status=True)
                return True
            elif temp_size > file_size:
                mode = 'wb'
                temp_size = 0
            else:
                mode = 'ab'
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
            self._print.download_info(path, status=False)
            return False
        self._print.download_info(path, status=True, t=download_bar.time, average_speed=download_bar.average_speed,
                                  refresh_line=True)
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
                GLOBAL_VAR.txt += share_txt
            else:
                for i in self._path_list.get_fid_list(file.id):
                    share_(path=None, file_id=i.id, parent_file=Path(parent_file) / file.name)

        GLOBAL_VAR.txt += '*' * 50 + '\n'
        GLOBAL_VAR.txt += '项目地址: https://github.com/wxy1343/aliyunpan' + '\n'
        GLOBAL_VAR.txt += '*' * 50 + '\n\n'
        share_(path, file_id)
        if save:
            file_name = Path(path).name + f'{int(time.time())}.txt'
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(GLOBAL_VAR.txt)
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

    def tui(self):
        aliyunpan_tui = AliyunpanTUI(self)
        aliyunpan_tui.run()
