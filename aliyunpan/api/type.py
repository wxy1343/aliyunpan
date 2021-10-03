from collections import namedtuple

__all__ = ['FileInfo', 'UserInfo', 'ShareInfo', 'AlibumInfo', 'Share']

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
