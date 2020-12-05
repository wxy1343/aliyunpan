import requests
import os
import hashlib
import time
import sys
import math
from multiprocessing.dummy import Pool, Queue
pool = Pool(5)
q = Queue(maxsize=5)


def get_list(Authorization, drive_id, parent_file_id='root'):
    """
    获取文件列表
    """
    url = 'https://api.aliyundrive.com/v2/file/list'
    headers = {'User-Agent': None, 'Authorization': Authorization}
    json = {"drive_id": drive_id, "parent_file_id": parent_file_id}
    r = requests.post(url, headers=headers, json=json)
    return r.json()


def get_user(Authorization):
    """
    获取用户信息
    """
    url = 'https://api.aliyundrive.com/v2/user/get'
    headers = {'User-Agent': None, 'Authorization': Authorization}
    r = requests.post(url, headers=headers, json={})
    return r.json()


def upload_file(Authorization, drive_id, parent_file_id='root', path=None):
    """
    上传文件
    """
    def upload(kwargs):
        part_number, upload_url, chunk = kwargs['part_number'], kwargs[
            'upload_url'], kwargs['chunk']
        size = len(chunk)
        if not chunk:
            return
        # 等待上一个线程上传完毕(本来想搞多线程上传的,但是网盘不支持,也懒得改了)
        while True:
            if part_number == 1:
                break
            data = q_pool.get()
            if data == part_number - 1:
                break
            else:
                q_pool.put(data)
        start_time = time.time()
        r = requests.put(upload_url, headers=headers, data=chunk)
        end_time = time.time()
        etag = r.headers['ETag']
        # 通知下一个线程上传
        q_pool.put(part_number)
        # 通知主线程
        q.put({
            'part_info_list': {
                'part_number': part_number,
                'etag': etag
            },
            'size': size,
            'time': end_time - start_time
        })

    split_size = 5242880 # 默认5MB分片大小(不要改)
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
        # 上传的目录(默认root就是主目录)
        "parent_file_id": parent_file_id,
        "part_info_list": part_info_list,
        "content_hash_name": "sha1",
        "content_hash": content_hash,
        # 如果文件存在则自动重命名(删了上传会出现名字一模一样的文件)
        "check_name_mode": "auto_rename"
    }
    # 申请创建文件
    url = 'https://api.aliyundrive.com/v2/file/create'
    headers = {'User-Agent': None, 'Authorization': Authorization}
    r = requests.post(url, headers=headers, json=json)
    # 如果存在匹配的hash值的文件则不会重复上传
    rapid_upload = r.json()['rapid_upload']
    if rapid_upload:
        print('快速上传成功')
    else:
        # 多线程队列
        q_pool = Queue(maxsize=5)
        upload_id = r.json()['upload_id']
        file_id = r.json()['file_id']
        part_info_list = r.json()['part_info_list']
        part_info_list_new = []
        total_time = 0
        count_size = 0
        k = 0
        sys.stdout.write(f'\r上传中... [{"*"*10}] %0')
        with open(path, 'rb') as f:
            # 开启多线程上传
            result = pool.map_async(upload, [{
                'part_number': i['part_number'],
                'upload_url': i['upload_url'],
                'chunk': f.read(split_size)
            } for i in part_info_list])
            # 等待线程通知
            while True:
                data = q.get()
                part_info_list_new.append(data['part_info_list'])
                size = data['size']
                total_time += data['time']
                k += size / file_size
                count_size += size
                sys.stdout.write(
                    f'\r上传中... [{"="*int(k*10)}{"*"*int((1-k)*10)}] %{math.ceil(k*1000)/10}'
                )
                if count_size == file_size:
                    break
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
                f'\n上传成功,耗时{int(total_time*100)/100}秒,平均速度{int(file_size/1024/1024/total_time*100)/100}MB/s'
            )
        else:
            print('\n上传失败')


if __name__ == '__main__':
    Authorization = '抓包获取access_token'
    user_info = get_user(Authorization)
    # 必要参数
    drive_id = user_info['default_drive_id']
    # get_list(Authorization, drive_id)
    upload_file(Authorization, drive_id, path='要上传的文件的路径')
