import math
import os
import sys
import time

import func_timeout
import requests

from aliyunpan.api.req import *
from aliyunpan.api.type import UserInfo
from aliyunpan.api.utils import *

__all__ = ['AliyunPan']


class AliyunPan(object):

    def __init__(self, refresh_token: str = None):
        self._req = Req()
        self._user_info = None
        self._access_token = None
        self._drive_id = None
        self._refresh_token = refresh_token
        self._access_token_gen_ = self._access_token_gen()
        self._drive_id_gen_ = self._drive_id_gen()

    refresh_token = property(lambda self: self._refresh_token,
                             lambda self, value: setattr(self, '_refresh_token', value))
    access_token = property(lambda self: next(self._access_token_gen_),
                            lambda self, value: setattr(self, '_access_token', value))
    drive_id = property(lambda self: next(self._drive_id_gen_),
                        lambda self, value: setattr(self, '_drive_id', value))

    def login(self, username: str, password: str):
        """
        登录api
        https://github.com/zhjc1124/aliyundrive
        :param username:
        :param password:
        :return:
        """
        password2 = encrypt(password)
        LOGIN = {
            'method': 'POST',
            'url': 'https://passport.aliyundrive.com/newlogin/login.do',
            'data': {
                'loginId': username,
                'password2': password2,
                'appName': 'aliyun_drive',
            }
        }
        logger.info('Logging in.')
        r = self._req.req(**LOGIN)
        if 'bizExt' in r.json()['content']['data']:
            data = parse_biz_ext(r.json()['content']['data']['bizExt'])
            logger.debug(data)
            self._access_token = data['pds_login_result']['accessToken']
            self._refresh_token = data['pds_login_result']['refreshToken']
            self._drive_id = data['pds_login_result']['defaultDriveId']
            return self._refresh_token
        return False

    def get_file_list(self, parent_file_id: str = 'root', next_marker: str = None) -> dict:
        """
        获取文件列表
        :param parent_file_id:
        :param next_marker:
        :return:
        """
        url = 'https://api.aliyundrive.com/v2/file/list'
        json = {"drive_id": self.drive_id, "parent_file_id": parent_file_id, 'fields': '*', 'marker': next_marker}
        headers = {'Authorization': self.access_token}
        logger.info(f'Get the list of parent_file_id {parent_file_id}.')
        r = self._req.post(url, headers=headers, json=json)
        logger.debug(r.status_code)
        if 'items' not in r.json():
            return False
        file_list = r.json()['items']
        if 'next_marker' in r.json() and r.json()['next_marker'] and next_marker != r.json()['next_marker']:
            file_list.extend(self.get_file_list(parent_file_id, r.json()['next_marker']))
        return file_list

    def delete_file(self, file_id: str):
        """
        删除文件
        :param file_id:
        :return:
        """
        url = 'https://api.aliyundrive.com/v2/batch'
        json = {'requests': [{'body': {'drive_id': self.drive_id, 'file_id': file_id},
                              'headers': {'Content-Type': 'application/json'},
                              'id': file_id, 'method': 'POST',
                              'url': '/recyclebin/trash'}], 'resource': 'file'}
        headers = {'Authorization': self.access_token}
        logger.info(f'Delete file {file_id}.')
        r = self._req.post(url, headers=headers, json=json)
        logger.debug(r.text)
        if r.status_code == 200:
            return r.json()['responses'][0]['id']
        return False

    def move_file(self, file_id: str, parent_file_id: str):
        """
        移动文件
        :param file_id:
        :param parent_file_id:
        :return:
        """
        url = 'https://api.aliyundrive.com/v2/batch'
        json = {"requests": [{"body": {"drive_id": self.drive_id, "file_id": file_id,
                                       "to_parent_file_id": parent_file_id},
                              "headers": {"Content-Type": "application/json"},
                              "id": file_id, "method": "POST", "url": "/file/move"}],
                "resource": "file"}
        headers = {'Authorization': self.access_token}
        logger.info(f'Move files {file_id} to {parent_file_id}')
        r = self._req.post(url, headers=headers, json=json)

        logger.debug(r.status_code)
        if r.status_code == 200:
            if 'message' in r.json()['responses'][0]['body']:
                print(r.json()['responses'][0]['body']['message'])
                return False
            return r.json()['responses'][0]['id']
        return False

    def get_user_info(self) -> UserInfo:
        """
        获取用户信息
        :return:
        """
        url = 'https://api.aliyundrive.com/v2/user/get'
        headers = {'Authorization': self.access_token}
        logger.info('Get user information.')
        r = self._req.post(url, headers=headers, json={})
        user_info = r.json()
        id_ = user_info['user_id']
        nick_name = user_info['nick_name']
        ctime = user_info['created_at']
        phone = user_info['phone']
        drive_id = user_info['default_drive_id']
        user_info = UserInfo(id=id_, nick_name=nick_name, ctime=ctime, phone=phone, drive_id=drive_id)
        logger.debug(user_info)
        return user_info

    def create_file(self, file_name: str, parent_file_id: str = 'root', file_type: bool = False,
                    json: dict = None, force: bool = False) -> requests.models.Response:
        """
        创建文件
        :param file_name:
        :param parent_file_id:
        :param file_type:
        :param json:
        :param force:
        :return:
        """
        j = {
            "name": file_name,
            "drive_id": self.drive_id,
            "parent_file_id": parent_file_id,
            "content_hash_name": "sha1",
        }
        if file_type:
            f_type = 'file'
            check_name_mode = 'auto_rename'
            if force:
                check_name_mode = 'refuse'
        else:
            f_type = 'folder'
            check_name_mode = 'refuse'
        j.update({"type": f_type, 'check_name_mode': check_name_mode})
        if json:
            j.update(json)
        # 申请创建文件
        url = 'https://api.aliyundrive.com/v2/file/create'
        headers = {'Authorization': self.access_token}
        logger.info(f'Create file {file_name} in file {parent_file_id}.')
        r = self._req.post(url, headers=headers, json=j)
        logger.debug(j)
        if force and 'exist' in r.json():
            self.delete_file(r.json()['file_id'])
            return self.create_file(file_name, parent_file_id, file_type, json)
        return r

    def upload_file(self, parent_file_id: str = 'root', path: str = None, upload_timeout: float = 10,
                    retry_num: int = 3, force: bool = False):
        """
        上传文件
        :param retry_num:
        :param parent_file_id: 上传目录的id
        :param path: 上传文件路径
        :param upload_timeout: 上传超时时间
        :param force: 强制覆盖
        :return:
        """
        split_size = 5242880  # 默认5MB分片大小(不要改)
        file_size = os.path.getsize(path)
        _, file_name = os.path.split(path)
        # 获取sha1
        content_hash = get_sha1(path, split_size)
        # 分片列表
        part_info_list = []
        count = int(file_size / split_size) + 1
        for i in range(count):
            part_info_list.append({"part_number": i + 1})
        json = {"size": file_size, "part_info_list": part_info_list, "content_hash": content_hash}
        print(f'[*][upload]{path}')
        # 申请创建文件
        r = self.create_file(file_name=file_name, parent_file_id=parent_file_id, file_type=True, json=json, force=force)
        if 'rapid_upload' not in r.json():
            message = r.json()['message']
            logger.error(message)
            raise Exception(message)
        rapid_upload = r.json()['rapid_upload']
        if rapid_upload:
            print(f'[+][upload]{path}\t快速上传成功')
            return r.json()['file_id']
        else:
            upload_id = r.json()['upload_id']
            file_id = r.json()['file_id']
            part_info_list = r.json()['part_info_list']
            part_info_list_new = []
            total_time = 0
            count_size = 0
            k = 0
            upload_info = f'\r上传中... [{"*" * 10}] %0'
            show_upload_info = upload_info and file_size >= 1024 * 1024
            for i in part_info_list:
                part_number, upload_url = i['part_number'], i['upload_url']
                with open(path, 'rb') as f:
                    f.seek((part_number - 1) * split_size)
                    chunk = f.read(split_size)
                if not chunk:
                    break
                size = len(chunk)
                retry_count = 0
                start_time = time.time()
                while True:
                    if show_upload_info:
                        sys.stdout.write(upload_info)
                        sys.stdout.flush()
                    try:
                        # 开始上传
                        r = func_timeout.func_timeout(upload_timeout,
                                                      lambda: self._req.put(upload_url, data=chunk))
                        logger.debug(i)
                        break
                    except func_timeout.exceptions.FunctionTimedOut:
                        logger.warn('Upload timeout.')
                        if retry_count is retry_num:
                            sys.stdout.write(f'\rError:上传超时{retry_num}次，即将重新上传'.ljust(30))
                            sys.stdout.flush()
                            time.sleep(1)
                            return self.upload_file(parent_file_id, path, upload_timeout)
                        sys.stdout.write(f'\rError:上传超时'.ljust(30))
                        sys.stdout.flush()
                        retry_count += 1
                        time.sleep(1)
                    except KeyboardInterrupt:
                        raise
                    except:
                        logger.error(sys.exc_info())
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        sys.stdout.write(f'\rError:{exc_type.__name__}'.ljust(30))
                        sys.stdout.flush()
                        time.sleep(1)
                    # 重试等待时间
                    n = 3
                    while n:
                        sys.stdout.write(f'\r{n}秒后重试'.ljust(30))
                        sys.stdout.flush()
                        n -= 1
                        time.sleep(1)
                    sys.stdout.write('\r')
                end_time = time.time()
                t = end_time - start_time
                total_time += t
                k += size / file_size
                count_size += size
                upload_info = f'\r上传中{"." * (part_number % 4)} [{"=" * int(k * 10)}{"*" * int((1 - k) * 10)}] %{math.ceil(k * 1000) / 10} {round(count_size / 1024 / 1024 / total_time, 2)}MB/s\t'
            # 上传完成保存文件
            url = 'https://api.aliyundrive.com/v2/file/complete'
            json = {
                "ignoreError": True,
                "drive_id": self.drive_id,
                "file_id": file_id,
                "upload_id": upload_id,
                "part_info_list": part_info_list_new
            }
            headers = {'Authorization': self.access_token}
            r = self._req.post(url, headers=headers, json=json)
            if r.status_code == 200:
                total_time = int(total_time * 100) / 100
                sys.stdout.write(
                    f'\r[+][upload]{path}\t上传成功,耗时{int(total_time * 100) / 100}秒,平均速度{round(file_size / 1024 / 1024 / total_time)}MB/s')
                sys.stdout.flush()
                return r.json()['file_id']
            else:
                sys.stdout.write(f'\r[-][upload]{path}')
                sys.stdout.flush()
                return False

    def get_access_token(self) -> str:
        """
        获取access_token
        :return:
        """
        # url = 'https://websv.aliyundrive.com/token/refresh'
        # json = {"refresh_token": self.refresh_token}
        url = 'https://auth.aliyundrive.com/v2/account/token'
        json = {"refresh_token": self.refresh_token, 'grant_type': 'refresh_token'}
        logger.info(f'Get ACCESS_TOKEN.')
        r = self._req.post(url, json=json)
        logger.debug(r.status_code)
        try:
            access_token = r.json()['access_token']
        except KeyError:
            raise Exception('Is not a valid refresh_token')
        logger.debug(access_token)
        return access_token

    def _access_token_gen(self) -> str:
        """
        access_token生成器
        :return:
        """
        access_token = None
        while True:
            if self._access_token:
                yield self._access_token
            elif access_token:
                yield access_token
            else:
                access_token = self.get_access_token()

    def get_drive_id(self) -> str:
        """
        获取drive_id
        :return:
        """
        return self.get_user_info().drive_id

    def _drive_id_gen(self) -> str:
        """
        drive_id生成器
        :return:
        """
        drive_id = None
        while True:
            if self._drive_id:
                yield self._drive_id
            elif drive_id:
                yield drive_id
            else:
                drive_id = self.get_drive_id()

    def get_download_url(self, file_id, expire_sec=14400) -> str:
        """
        获取分享链接
        :param file_id:
        :param expire_sec: 文件过期时间（秒）
        :return:
        """
        url = 'https://api.aliyundrive.com/v2/file/get_download_url'
        headers = {'Authorization': self.access_token}
        json = {'drive_id': self.drive_id, 'file_id': file_id, 'expire_sec': expire_sec}
        logger.info(f'Get file {file_id} download link, expiration time {expire_sec} seconds.')
        r = self._req.post(url, json=json, headers=headers)
        logger.debug(r.status_code)
        url = r.json()['url']
        logger.debug(f'file_id:{file_id},expire_sec:{expire_sec},url:{url}')
        return url

    def save_share_link(self, name: str, content_hash: str, content_hash_name: str, size: str,
                        parent_file_id: str = 'root', force: bool = False) -> bool:
        """
        保存分享文件
        :param content_hash_name:
        :param name:
        :param content_hash:
        :param size:
        :param parent_file_id:
        :param force:
        :return:
        """
        logger.info(f'name: {name}, content_hash:{content_hash}, size:{size}')
        json = {'content_hash': content_hash, 'size': int(size), 'content_hash_name': content_hash_name or 'sha1'}
        r = self.create_file(name, parent_file_id=parent_file_id, file_type=True, json=json, force=force)
        if r.status_code == 201 and 'rapid_upload' in r.json() and r.json()['rapid_upload']:
            return r.json()['file_id']
        elif 'message' in r.json():
            print(r.json()["message"])
        return False
