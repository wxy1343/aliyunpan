from collections import namedtuple
from pathlib import Path

__all__ = ['FileInfo', 'UserInfo', 'ShareInfo', 'AlibumInfo', 'Share', 'File']

_file_info = (
    'name', 'id', 'pid', 'type', 'ctime', 'update_time', 'hidden', 'category', 'content_type', 'size',
    'content_hash_name',
    'content_hash', 'download_url',
    'video_media_metadata', 'video_preview_metadata')
FileInfo = namedtuple('FileInfo', _file_info)
FileInfo.__new__.__defaults__ = ('',) * len(_file_info)
UserInfo = namedtuple('UserInfo', ['id', 'nick_name', 'ctime', 'phone', 'drive_id'])
UserInfo.__new__.__defaults__ = ('',) * 5
ShareInfo = namedtuple('ShareInfo', ['name', 'content_hash', 'proof_code', 'content_hash_name', 'size', 'path'])
ShareInfo.__new__.__defaults__ = ('',) * 6
AlibumInfo = namedtuple('AlibumInfo', ['drive_name', 'drive_id'])
AlibumInfo.__new__.__defaults__ = ('',) * 2


class Share:
    share_id = ''
    share_pwd = ''
    share_token = ''

    def __init__(self, share_id='', share_pwd='', share_token=''):
        self.share_id = share_id
        self.share_pwd = share_pwd
        self.share_token = share_token


class File:
    def __init__(self, file_id: str, path: Path):
        self.file_id = file_id
        self.path = path

    def __getitem__(self, item):
        if item == 0:
            return self.file_id
        elif item == 1:
            return self.path
        return getattr(self, item)

    def __iter__(self):
        return iter((self.file_id, self.path))

    def __str__(self):
        return f'{self.file_id} -> {self.path}'
