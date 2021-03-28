from collections import namedtuple

__all__ = ['FileInfo', 'UserInfo']

_base_info = ['name', 'id', 'pid', 'type', 'ctime', 'update_time', 'hidden']
_file_info = (*_base_info, 'category', 'size', 'content_hash_name', 'content_hash', 'download_url')
FileInfo = namedtuple('FileInfo', _file_info, defaults=('',) * len(_file_info))
UserInfo = namedtuple('UserInfo', ['id', 'nick_name', 'ctime', 'phone', 'drive_id'], defaults=('',) * 5)
