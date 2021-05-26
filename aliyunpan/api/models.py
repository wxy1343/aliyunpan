import time
from pathlib import Path, PurePosixPath

from treelib import Tree

from aliyunpan.api.type import FileInfo, ShareInfo

_all_ = ['PathList', 'parse_share_url']


class PathList:
    def __init__(self, disk):
        self._tree = Tree()
        self._disk = disk
        self._tree.create_node(tag='root', identifier='root')
        self.depth = 3

    def update_path_list(self, file_id='root', depth=None, is_fid=True):
        if depth is None:
            depth = self.depth
        if not is_fid:
            file_id = self.get_path_fid(file_id, update=False)
        file_list = self._disk.get_file_list(file_id)
        if not file_list:
            return False
        for i in file_list:
            if i['type'] == 'file':
                file_info = FileInfo(name=i['name'], id=i['file_id'], pid=i['parent_file_id'], type=True,
                                     ctime=time.strptime(i['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                                     update_time=time.strptime(i['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                                     hidden=i['hidden'], category=i['category'], content_type=i['content_type'],
                                     size=i['size'], content_hash_name=i['content_hash_name'],
                                     content_hash=i['content_hash'],
                                     download_url=i['download_url'] if 'download_url' in i else '',
                                     video_media_metadata=i[
                                         'video_media_metadata'] if 'video_media_metadata' in i else None,
                                     video_preview_metadata=i[
                                         'video_preview_metadata'] if 'video_preview_metadata' in i else None)
            else:
                file_info = FileInfo(name=i['name'], id=i['file_id'], pid=i['parent_file_id'], type=False,
                                     ctime=time.strptime(i['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                                     update_time=time.strptime(i['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                                     hidden=i['hidden'])
            if self._tree.get_node(file_info.id):
                self._tree.update_node(file_info.id, data=file_info)
            else:
                self._tree.create_node(tag=file_info.name, identifier=file_info.id, data=file_info, parent=file_id)
            if not file_info.type and depth:
                self.update_path_list(file_id=file_info.id, depth=depth - 1)
        return True

    def tree(self, path='root'):
        file_id = self.get_path_fid(path, update=False)
        self.update_path_list(file_id)
        if not file_id:
            raise FileNotFoundError(path)
        self._tree.show(file_id)

    def get_path_list(self, path, update=True):
        file_id = self.get_path_fid(path, update=update)
        return self.get_fid_list(file_id, update=update)

    def get_fid_list(self, file_id, update=True):
        if not file_id:
            raise FileNotFoundError(Path)
        self.auto_update_path_list(update, file_id)
        if file_id != 'root' and self._tree.get_node(file_id).data.type:
            return [self._tree.get_node(file_id).data]
        return [i.data for i in self._tree.children(file_id)]

    def get_path_fid(self, path, file_id='root', update=True):
        path = PurePosixPath(Path(path).as_posix())
        if str(path) in ('', '/', '\\', '.', 'root'):
            return 'root'
        flag = False
        path_list = list(filter(None, str(path).split('/')))
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


def parse_share_url(url):
    name, content_hash, size, path = url.split('aliyunpan://')[1].split('|')[:4]
    split_list = [':', '=']
    content_hash_name = ''
    for i in split_list:
        if i in content_hash:
            content_hash_name, content_hash = content_hash.split(i)
            break
    share_info = ShareInfo(name=name, content_hash=content_hash, content_hash_name=content_hash_name, size=size,
                           path=Path(path.strip()))
    return share_info
