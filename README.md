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

## 配置账号(可选)

```shell
$ echo "username: 'xxxxx'"  >  ~/.config/aliyunpan.yaml
$ echo "password: 'xxxxx'"  >  ~/.config/aliyunpan.yaml
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

|参数                |描述                            |
|--------------------|------------------------------|
|-h, --help          |查看帮助                        |
|--version           |查看版本                        |
|-c, --config-file   |指定配置文件                     |
|-t                  |指定REFRESH_TOKEN              |
|-u                  |指定账号                        |
|-p                  |指定密码                        |
|-d, --depth         |文件递归深度                     | 

* 查看指令参数

```shell
$ python main.py COMMAND -h
```

|指令                |参数                 |描述                           |
|-------------------|--------------------|------------------------------|
|download           |-p, --file          |选择文件(多个)                   |
|ls                 |-l                  |查看详情                        |
|share              |-f, --file-id       |指定file_id                    |
|share              |-t, --expire-sec    |分享过期时间(秒)，默认最大14400    |
|upload             |-p, --file          |选择文件(多个)                   |
|upload             |-t, --time-out      |上传超时时间(秒)                  |
|upload             |-r, --retry         |上传失败重试次数                  |
|upload             |-f, --force         |强制覆盖文件                     |

# 致谢

感谢 [zhjc1124/aliyundrive](https://github.com/zhjc1124/aliyundrive) 的登录接口参考