import asyncio
import hashlib
import math
import os
import sys
import time

import nest_asyncio
import requests
from aiofile import async_open

from aliyunpan.api.req import *
from aliyunpan.api.type import UserInfo
from aliyunpan.api.utils import *

__all__ = ['AliyunPan']

nest_asyncio.apply()


class AliyunPan(object):

    def __init__(self, refresh_token: str = None):
        self._req = Req()
        self._loop = asyncio.get_event_loop()
        self._user_info = None
        self._refresh_token = refresh_token
        self._access_token_gen = self.get_access_token()
        self._drive_id_gen = self.get_drive_id()

    refresh_token = property(lambda self: self._refresh_token,
                             lambda self, value: setattr(self, '_refresh_token', value))
    access_token = property(lambda self: next(self._access_token_gen))
    drive_id = property(lambda self: next(self._drive_id_gen))

    @run
    async def get_file_list(self, parent_file_id: str = 'root') -> dict:
        """
        获取文件列表
        """
        url = 'https://api.aliyundrive.com/v2/file/list'
        json = {"drive_id": self.drive_id, "parent_file_id": parent_file_id}
        headers = {'Authorization': self.access_token}
        r = await self._req.post_async(url, headers=headers, json=json)
        return r.json()

    @run
    async def delete_file(self, file_id: str):
        """
        删除文件
        """
        url = 'https://api.aliyundrive.com/v2/batch'
        json = {'requests': [{'body': {'drive_id': self.drive_id, 'file_id': file_id},
                              'headers': {'Content-Type': 'application/json'},
                              'id': file_id, 'method': 'POST',
                              'url': '/recyclebin/trash'}], 'resource': 'file'}
        headers = {'Authorization': self.access_token}
        r = await self._req.post_async(url, headers=headers, json=json)
        if r.status_code == 200:
            return True
        return False

    @run
    async def move_file(self, file_id: str, path_file_id: str):
        """
        移动文件
        """
        url = 'https://api.aliyundrive.com/v2/batch'
        json = {"requests": [{"body": {"drive_id": self.drive_id, "file_id": file_id,
                                       "to_parent_file_id": path_file_id},
                              "headers": {"Content-Type": "application/json"},
                              "id": file_id, "method": "POST", "url": "/file/move"}],
                "resource": "file"}
        headers = {'Authorization': self.access_token}
        r = await self._req.post_async(url, headers=headers, json=json)
        if r.status_code == 200:
            return True
        return False

    async def get_user_info(self) -> UserInfo:
        """
        获取用户信息
        :return:
        """
        url = 'https://api.aliyundrive.com/v2/user/get'
        headers = {'Authorization': self.access_token}
        r = await self._req.post_async(url, headers=headers, json={})
        user_info = r.json()
        id_ = user_info['user_id']
        nick_name = user_info['nick_name']
        ctime = user_info['created_at']
        phone = user_info['phone']
        drive_id = user_info['default_drive_id']
        user_info = UserInfo(id=id_, nick_name=nick_name, ctime=ctime, phone=phone, drive_id=drive_id)
        logger.debug(user_info)
        return user_info

    @run
    async def create_file(self, file_name: str, parent_file_id: str = 'root', file_type: bool = False,
                          json: dict = None, force: bool = False):
        """
        创建文件
        """
        if parent_file_id == '' or parent_file_id == '/':
            parent_file_id = 'root'
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
        r = await self._req.post_async(url, headers=headers, json=j)
        logger.debug(j)
        if force and 'exist' in r.json():
            self.delete_file(r.json()['file_id'])
            return self.create_file(file_name, parent_file_id, file_type, json)
        return r

    @run
    async def upload_file(self, parent_file_id: str = 'root', path: str = None, upload_timeout: float = 10,
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
        if parent_file_id == '' or parent_file_id == '/':
            parent_file_id = 'root'
        split_size = 5242880  # 默认5MB分片大小(不要改)
        file_size = os.path.getsize(path)
        _, file_name = os.path.split(path)
        # 获取sha1
        async with async_open(path, 'rb') as f:
            sha1 = hashlib.sha1()
            count = 0
            while True:
                chunk = await f.read(split_size)
                if not chunk:
                    break
                count += 1
                sha1.update(chunk)
            content_hash = sha1.hexdigest()
        # 分片列表
        part_info_list = []
        for i in range(count):
            part_info_list.append({"part_number": i + 1})
        json = {"size": file_size, "part_info_list": part_info_list, "content_hash": content_hash}
        # 申请创建文件
        r = self.create_file(file_name, parent_file_id, True, json, force)
        if r.json()['rapid_upload']:
            print(path, '快速上传成功')
        else:
            upload_id = r.json()['upload_id']
            file_id = r.json()['file_id']
            part_info_list = r.json()['part_info_list']
            part_info_list_new = []
            total_time = 0
            count_size = 0
            k = 0
            upload_info = f'\r上传中... [{"*" * 10}] %0'
            for i in part_info_list:
                part_number, upload_url = i['part_number'], i['upload_url']
                async with async_open(path, 'rb') as f:
                    f.seek((part_number - 1) * split_size)
                    chunk = await f.read(split_size)
                if not chunk:
                    break
                size = len(chunk)
                retry_count = 0
                start_time = time.time()
                while True:
                    if upload_info:
                        sys.stdout.write(upload_info)
                    try:
                        # 开始上传
                        r = await self._req.put_async(upload_url, data=chunk, async_timeout=upload_timeout)
                        logger.debug(i)
                        break
                    except requests.exceptions.RequestException:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        sys.stdout.write(f'\rError:{exc_type.__name__}')
                        await asyncio.sleep(1)
                    except asyncio.exceptions.TimeoutError:
                        if retry_count is retry_num:
                            sys.stdout.write(f'\rError:上传超时{retry_num}次，即将重新上传')
                            await asyncio.sleep(1)
                            return self.upload_file(parent_file_id, path, upload_timeout)
                        sys.stdout.write(f'\rError:上传超时')
                        retry_count += 1
                        await asyncio.sleep(1)
                    # 重试等待时间
                    n = 3
                    while n:
                        sys.stdout.write(f'\r{n}秒后重试')
                        n -= 1
                        await asyncio.sleep(1)
                    sys.stdout.write('\r')
                end_time = time.time()
                t = end_time - start_time
                total_time += t
                k += size / file_size
                count_size += size
                upload_info = f'\r上传中{"." * (part_number % 4)} [{"=" * int(k * 10)}{"*" * int((1 - k) * 10)}] %{math.ceil(k * 1000) / 10} {round(count_size / 1024 / 1024 / total_time, 2)}MB/s'
                sys.stdout.write(upload_info)
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
            r = await self._req.post_async(url, headers=headers, json=json)
            if r.status_code == 200:
                total_time = int(total_time * 100) / 100
                print(f'\n上传成功,耗时{int(total_time * 100) / 100}秒,平均速度{round(file_size / 1024 / 1024 / total_time)}MB/s',
                      path)
            else:
                print('\n上传失败', path)

    def get_access_token(self) -> str:
        """
        获取access_token
        """
        access_token = None
        url = 'https://websv.aliyundrive.com/token/refresh'
        json = {"refresh_token": self.refresh_token}
        while True:
            if access_token:
                yield access_token
            else:
                r = self._req.post(url, json=json)
                access_token = r.json()['access_token']

    def get_drive_id(self) -> str:
        """
        获取drive_id
        """
        drive_id = None
        while True:
            if drive_id:
                yield drive_id
            else:
                drive_id = self._loop.run_until_complete(self.get_user_info()).drive_id
