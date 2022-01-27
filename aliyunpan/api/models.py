import base64
import sys
import time
from pathlib import Path, PurePosixPath

from treelib import Tree
from treelib.exceptions import NodeIDAbsentError

from aliyunpan.api.type import FileInfo, ShareInfo
from aliyunpan.api.utils import get_sha1, get_url_byte, get_proof_code
from aliyunpan.common import GetFileListBar

_all_ = ['PathList', 'parse_share_url', 'AliyunpanPath']


class PathList:
    def __init__(self, disk):
        self._tree = Tree()
        self._disk = disk
        self._tree.create_node(tag='root', identifier='root', data=FileInfo(type=False))
        self.depth = 3

    def update_path_list(self, file_id='root', depth=None, is_fid=True, **kwargs):
        if depth is None:
            depth = self.depth
        kwargs.setdefault('max_depth', depth)
        max_depth = kwargs['max_depth']
        kwargs.setdefault('get_file_list_bar', GetFileListBar(max_depth))
        kwargs.setdefault('ratio', 0)
        get_file_list_bar = kwargs['get_file_list_bar']
        ratio = kwargs['ratio']
        get_file_list_bar.update(refresh_line=False)
        if not is_fid:
            file_id = self.get_path_fid(file_id, update=False)
        file_list = self._disk.get_file_list(file_id)
        if not file_list:
            if depth == max_depth:
                get_file_list_bar.refresh_line()
            return False
        old_file_list = self._tree.children(file_id)
        for i in old_file_list:
            if i.identifier not in [j['file_id'] for j in file_list]:
                self._tree.remove_node(i.identifier)
        for i, info in enumerate(file_list):
            if depth == max_depth:
                ratio = (i + 1) / len(file_list) if file_list else None
            get_file_list_bar.update(depth=max_depth - depth, ratio=ratio, refresh_line=True)
            file_info = self.get_file_info(info)[0]
            if self._tree.get_node(file_info.id):
                self._tree.update_node(file_info.id, data=file_info)
            else:
                self._tree.create_node(tag=file_info.name, identifier=file_info.id, data=file_info, parent=file_id)
            if not file_info.type and depth:
                self.update_path_list(file_id=file_info.id, depth=depth - 1, max_depth=max_depth,
                                      get_file_list_bar=get_file_list_bar, ratio=ratio)
        if depth == max_depth:
            get_file_list_bar.refresh_line()
        return True

    def check_path_diff(self, local_path, disk_path_list):
        p = Path(local_path)
        change_file_list = []
        for path in p.iterdir():
            flag = False
            for i, path_ in enumerate(disk_path_list, 1):
                name, file_info = list(path_.items())[0]
                if p / name not in p.iterdir():
                    change_file_list.append(p / name)
                if Path(path) == p / name:
                    if Path(path).is_dir() and file_info['data'] and path.is_dir() != file_info['data'].type:
                        if 'children' in file_info:
                            children = file_info['children']
                            change_file_list.extend(self.check_path_diff(p / name, children))
                        elif list(path.iterdir()):
                            change_file_list.extend(list(path.iterdir()))
                    if file_info and file_info['data'] and path.is_file() == file_info['data'].type:
                        if path.is_file() and get_sha1(path).lower() != file_info['data'].content_hash.lower():
                            if i == len(disk_path_list):
                                change_file_list.append(path)
                            continue
                        else:
                            flag = True
                if not flag and i == len(disk_path_list):
                    change_file_list.append(path)
        if not len(list(p.iterdir())):
            for path_ in disk_path_list:
                name, file_info = list(path_.items())[0]
                change_file_list.append(p / name)
        if not len(disk_path_list):
            for path_ in p.iterdir():
                change_file_list.append(path_)
        return list(set(change_file_list))

    @staticmethod
    def get_file_info(info):
        file_info_list = []
        if not isinstance(info, list):
            info_list = [info]
        else:
            info_list = info
        for info in info_list:
            if info['type'] == 'file':
                file_info = FileInfo(name=info['name'], id=info['file_id'], pid=info['parent_file_id'], type=True,
                                     ctime=time.strptime(info['created_at'],
                                                         '%Y-%m-%dT%H:%M:%S.%fZ') if 'created_at' in info else time.localtime(),
                                     update_time=time.strptime(info['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                                     hidden=info.get('hidden'), category=info['category'],
                                     content_type=info.get('content_type'),
                                     size=info['size'], content_hash_name=info.get('content_hash_name'),
                                     content_hash=info.get('content_hash'),
                                     download_url=info['download_url'] if 'download_url' in info else '',
                                     video_media_metadata=info[
                                         'video_media_metadata'] if 'video_media_metadata' in info else None,
                                     video_preview_metadata=info[
                                         'video_preview_metadata'] if 'video_preview_metadata' in info else None)
            else:
                file_info = FileInfo(name=info['name'], id=info['file_id'], pid=info['parent_file_id'], type=False,
                                     ctime=time.strptime(info['created_at'],
                                                         '%Y-%m-%dT%H:%M:%S.%fZ') if 'created_at' in info else time.time(),
                                     update_time=time.strptime(info['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                                     hidden=info.get('hidden'))
            file_info_list.append(file_info)
        return file_info_list

    def tree(self, path='root', stdout=sys.stdout):
        file_id = self.get_path_fid(path, update=False)
        self.update_path_list(file_id)
        if not file_id:
            raise FileNotFoundError(path)
        return self._tree.show(file_id, stdout=stdout)

    def get_path_list(self, path, update=True):
        file_id = self.get_path_fid(path, update=update)
        try:
            return self.get_fid_list(file_id, update=update)
        except FileNotFoundError:
            raise FileNotFoundError(path)

    def get_fid_list(self, file_id, update=True):
        if not file_id:
            raise FileNotFoundError
        try:
            self.auto_update_path_list(update, file_id)
        except NodeIDAbsentError:
            return list(map(self.get_file_info, self._disk.get_file_list(file_id)))
        if not self._tree.get_node(file_id):
            return []
        if file_id != 'root' and self._tree.get_node(file_id).data.type:
            return [self._tree.get_node(file_id).data]
        return [i.data for i in self._tree.children(file_id)]

    def get_path_fid(self, path, file_id='root', update=True):
        if str(path) in ('', '/', '\\', '.', 'root'):
            return 'root'
        path = AliyunpanPath(path)
        flag = False
        path_list = list(filter(None, path.split()))
        if path_list[0] == 'root':
            path_list = path_list[1:]
        for i in path_list:
            flag = False
            node_list = self._tree.children(file_id)
            if not node_list:
                self.auto_update_path_list(update, file_id)
                node_list = self._tree.children(file_id)
            for j in node_list:
                if i == j.tag:
                    flag = True
                    file_id = j.identifier
                    break
            if not flag:
                return False
        if flag:
            return file_id
        return False

    def get_path_node(self, path, update=True):
        file_id = self.get_path_fid(path, update=update)
        if file_id:
            return self._tree.get_node(file_id)
        return False

    def get_path_parent_node(self, path, update=True):
        file_id = self.get_path_fid(path, update=update)
        if file_id:
            node = self._tree.parent(file_id)
            if node:
                return node
        return False

    def auto_update_path_list(self, update=True, file_id=None):
        if not update and file_id:
            return self.update_path_list(file_id, depth=0)
        elif update and len(self._tree) == 1:
            return self.update_path_list()


def parse_share_url(url, access_token):
    name, content_hash, url, size, path = url.split('aliyunpan://')[1].split('|')[:5]
    url = base64.b64decode(url).decode()
    split_list = [':', '=']
    content_hash_name = ''
    for i in split_list:
        if i in content_hash:
            content_hash_name, content_hash = content_hash.split(i)
            break
    proof_code = get_proof_code(get_url_byte(url, access_token, int(size)))
    share_info = ShareInfo(name=name, content_hash=content_hash, proof_code=proof_code,
                           content_hash_name=content_hash_name, size=size, path=Path(path.strip()))
    return share_info


class AliyunpanPath(type(Path())):
    def __str__(self):
        p = super().__str__()
        path = [i for i in str(PurePosixPath(Path(p).as_posix())).split('/') if i != '']
        if not path:
            path = ['root']
        if len(path) != 1 and path[0] == 'root':
            path = path[1:]
        path = ('/' if p[0] in ['/', '\\'] else '') + '/'.join(path)
        return path

    def split(self):
        return self.__str__().split('/')

    def __eq__(self, other):
        if self.__str__() == other.__str__():
            return True

    def __hash__(self):
        return hash(self.__str__())

    def __sub__(self, other: Path):
        parts = []
        parts1 = self.parts
        parts2 = other.parts
        if len(other.parts) > len(self.parts):
            parts1, parts2 = parts2, parts1
        for i, j in enumerate(parts1):
            if len(parts2) >= i + 1:
                if j != other.parts[i]:
                    parts.append(j)
            else:
                parts.append(j)
        return AliyunpanPath('/'.join(parts))

    def __add__(self, other):
        return Path(self.__str__()) / Path(str(other))

    @property
    def parent(self):
        p = self.__str__()
        p_ = p.rsplit('/', 1)[0]
        return 'root' if p_ == p else p_
