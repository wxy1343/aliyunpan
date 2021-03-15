import hashlib
import math
import os
import sys
import time
import func_timeout
import requests


def get_list(access_token, drive_id, parent_file_id='root'):
    """
    获取文件列表
    """
    url = 'https://api.aliyundrive.com/v2/file/list'
    headers = {'User-Agent': None, 'Authorization': access_token}
    json = {"drive_id": drive_id, "parent_file_id": parent_file_id}
    r = requests.post(url, headers=headers, json=json)
    return r.json()


def get_user(access_token):
    """
    获取用户信息
    """
    url = 'https://api.aliyundrive.com/v2/user/get'
    headers = {'User-Agent': None, 'Authorization': access_token}
    r = requests.post(url, headers=headers, json={})
    return r.json()


def refresh(refresh_token):
    """
    获取access_token
    :param refresh_token:
    :return: _access_token
    """
    url = 'https://websv.aliyundrive.com/token/refresh'
    json = {"refresh_token": refresh_token}
    headers = {'User-Agent': None}
    r = requests.post(url, json=json, headers=headers)
    return r.json()['access_token']


def upload_file(access_token, drive_id, parent_file_id='root', path=None, timeout=10, retry_num=3):
    """
    上传文件
    :param retry_num:
    :param access_token:
    :param drive_id:
    :param parent_file_id: 上传目录的id
    :param path: 上传文件路径
    :param timeout: 上传超时时间
    :return:
    """
    split_size = 5242880  # 默认5MB分片大小(不要改)
    file_size = os.path.getsize(path)
    _, file_name = os.path.split(path)
    # 获取sha1
    with open(path, 'rb') as f:
        sha1 = hashlib.sha1()
        count = 0
        while True:
            chunk = f.read(split_size)
            if not chunk:
                break
            count += 1
            sha1.update(chunk)
        content_hash = sha1.hexdigest()
    # 分片列表
    part_info_list = []
    for i in range(count):
        part_info_list.append({"part_number": i + 1})
    json = {
        "name": file_name,
        "type": "file",
        "size": file_size,
        "drive_id": drive_id,
        "parent_file_id": parent_file_id,
        "part_info_list": part_info_list,
        "content_hash_name": "sha1",
        "content_hash": content_hash,
        # 如果文件存在则自动重命名(删了上传会出现名字一模一样的文件)
        "check_name_mode": "auto_rename"
    }
    # 申请创建文件
    url = 'https://api.aliyundrive.com/v2/file/create'
    headers = {'User-Agent': None, 'Authorization': access_token}
    r = requests.post(url, headers=headers, json=json)
    # 如果存在匹配的hash值的文件则不会重复上传
    rapid_upload = r.json()['rapid_upload']
    if rapid_upload:
        print('快速上传成功')
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
            with open(path, 'rb') as f:
                f.seek((part_number - 1) * split_size)
                chunk = f.read(split_size)
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
                    func_timeout.func_timeout(timeout, lambda: requests.put(upload_url, headers=headers, data=chunk,
                                                                            timeout=timeout))
                    break
                except requests.exceptions.RequestException:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    sys.stdout.write(f'\rError:{exc_type.__name__}')
                    time.sleep(1)
                except func_timeout.exceptions.FunctionTimedOut:
                    if retry_count is retry_num:
                        sys.stdout.write(f'\rError:上传超时{retry_num}次，即将重新上传')
                        time.sleep(1)
                        return upload_file(access_token, drive_id, parent_file_id, path, timeout)
                    sys.stdout.write(f'\rError:上传超时')
                    retry_count += 1
                    time.sleep(1)
                # 重试等待时间
                n = 3
                while n:
                    sys.stdout.write(f'\r{n}秒后重试')
                    n -= 1
                    time.sleep(1)
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
            "drive_id": drive_id,
            "file_id": file_id,
            "upload_id": upload_id,
            "part_info_list": part_info_list_new
        }
        r = requests.post(url, headers=headers, json=json)
        if r.status_code == 200:
            total_time = int(total_time * 100) / 100
            print(
                f'\n上传成功,耗时{int(total_time * 100) / 100}秒,平均速度{round(file_size / 1024 / 1024 / total_time)}MB/s'
            )
        else:
            print('\n上传失败')


if __name__ == '__main__':
    refresh_token = '在Chrome DevTools Application中获取'
    access_token = refresh(refresh_token)
    user_info = get_user(access_token)
    drive_id = user_info['default_drive_id']
    # get_list(access_token, drive_id)
    upload_file(access_token, drive_id, path='文件路径', timeout=15)
