import time

from treelib import Tree

from aliyunpan.api.type import FileInfo


class PathList:
    def __init__(self, disk):
        self._tree = Tree()
        self._disk = disk
        self._tree.create_node(tag='root', identifier='root')

    def update_path_list(self, path='root', depth=3):
        for i in self._disk.get_file_list(path)['items']:
            if i['type'] == 'file':
                file_info = FileInfo(name=i['name'], id=i['file_id'], pid=i['parent_file_id'], type=True,
                                     ctime=time.strptime(i['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                                     update_time=time.strptime(i['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                                     hidden=i['hidden'],
                                     category=i['category'], size=i['size'], content_hash_name=i['content_hash_name'],
                                     content_hash=i['content_hash'], download_url=i['download_url'])
            else:
                file_info = FileInfo(name=i['name'], id=i['file_id'], pid=i['parent_file_id'], type=False,
                                     ctime=time.strptime(i['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                                     update_time=time.strptime(i['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                                     hidden=i['hidden'])
            self._tree.create_node(tag=file_info.name, identifier=file_info.id, data=file_info, parent=path)
            if not file_info.type and depth:
                self.update_path_list(path=file_info.id, depth=depth - 1)

    def tree(self, path):
        if len(self._tree) == 1:
            self.update_path_list()
        elif len(self._tree) > 1:
            self.__init__(self._disk)
            self.update_path_list()
        file_id = self.get_path_fid(path)
        if not file_id:
            raise Exception('No such file or directory')
        self._tree.show(file_id)

    def get_path_list(self, path):
        file_id = self.get_path_fid(path)
        if not file_id:
            raise Exception('No such file or directory')
        if file_id != 'root' and self._tree.get_node(file_id).data.type:
            return [self._tree.get_node(file_id).data]
        return [i.data for i in self._tree.children(file_id)]

    def get_path_fid(self, path, file_id='root'):
        if len(self._tree) == 1:
            self.update_path_list()
        elif len(self._tree) > 1:
            self.__init__(self._disk)
            self.update_path_list()
        if path == '/' or path == '' or path == 'root':
            return 'root'
        flag = False
        for i in filter(None, path.split('/')):
            flag = False
            for j in self._tree.children(file_id):
                if i == j.tag:
                    flag = True
                    file_id = j.identifier
                    break
        if flag:
            return file_id
        return False
