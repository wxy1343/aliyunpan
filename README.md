# aliyunpan

阿里云盘cli

# 获取refresh_token

![token](https://github.com/wxy1343/aliyunpan/raw/main/token.png)

## 注意

* web端获取的refresh_token暂时无法分享
* 可以通过手机端查找日志获取refresh_token

> /sdcard/Android/data/com.alicloud.databox/files/logs/trace/userId/yunpan/latest.log

## 配置refresh_token

```shell
$ echo "refresh_token: 'xxxxx'"  >  ~/.config/aliyunpan.yaml
```

# 功能

|指令                 |描述                           |
|--------------------|------------------------------|
|download (d)        |下载文件/文件夹                  |
|ls (dir,l,list)     |列目录                         |
|mv (move)           |移动文件/文件夹                  |
|rm (del,delete)     |删除文件/文件夹                  |
|tree (show,t)       |查看文件树                      |
|upload (u)          |上传文件/文件夹                  |
|share (s)           |分享文件                        |
|mkdir (m)           |创建文件夹                      |

# 使用指南

* 查看帮助

```shell
$ python main.py -h
```

* 查看指令参数

```shell
$ python main.py COMMAND -h
```