from collections import namedtuple

__all__ = ['FileInfo', 'UserInfo', 'ShareInfo']

_base_info = ['name', 'id', 'pid', 'type', 'ctime', 'update_time', 'hidden']
_file_info = (*_base_info, 'category', 'content_type', 'size', 'content_hash_name', 'content_hash', 'download_url')
FileInfo = namedtuple('FileInfo', _file_info, defaults=('',) * len(_file_info))
UserInfo = namedtuple('UserInfo', ['id', 'nick_name', 'ctime', 'phone', 'drive_id'], defaults=('',) * 5)
ShareInfo = namedtuple('ShareInfo', ['name', 'content_hash', 'content_hash_name', 'size', 'path'], defaults=('',) * 5)
