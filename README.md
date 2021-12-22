# aliyunpan

[![Build Status](https://github.com/wxy1343/aliyunpan/workflows/CI/badge.svg)](https://github.com/wxy1343/aliyunpan/actions)
[![GitHub](https://img.shields.io/github/license/wxy1343/aliyunpan)](https://github.com/wxy1343/aliyunpan/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/aliyunpan)](https://pypi.org/project/aliyunpan/)
[![GitHub all releases](https://img.shields.io/github/downloads/wxy1343/aliyunpan/total)](https://github.com/wxy1343/aliyunpan/releases/latest/)
[![wiki](https://img.shields.io/badge/-wiki-ff69b4)](https://github.com/wxy1343/aliyunpan/wiki)

---

阿里云盘cli  
环境要求： python 3.7 通过测试  
~~低版本环境运行报错参考~~[~~issue9~~](https://github.com/wxy1343/aliyunpan/issues/9)

## 安装

```shell
pip install aliyunpan
```

## 更新

```shell
pip install aliyunpan --upgrade
```

## 运行

```shell
aliyunpan-cli
```

## pyinstaller打包

[最新版下载](https://github.com/wxy1343/aliyunpan/releases/latest) (GitHub
Actions打包，glibc版本较高 [#42](https://github.com/wxy1343/aliyunpan/issues/42))  
[第三方下载](https://media.cooluc.com/source/aliyunDrive-cli) (更新较慢)

## 克隆项目

* `--recurse-submodules` 用于克隆子模块，部分功能需要(可选)

```shell
git clone https://github.com/wxy1343/aliyunpan --recurse-submodules
```

## 获取refresh_token

![token](https://github.com/wxy1343/aliyunpan/raw/main/token.png)

### 注意

* web端获取的refresh_token有防盗链检测

1. 可以指定账号密码登入
2. 可以通过手机端查找日志获取refresh_token

> /sdcard/Android/data/com.alicloud.databox/files/logs/trace/userId/yunpan/latest.log

* ~~登录api加入了ua检测，需要运行混淆的js代码来获取ua~~
* ~~推荐安装 [node.js](https://nodejs.org) 和 [jsdom](https://github.com/jsdom/jsdom) 模块来运行js代码~~
* 目前阿里云盘修改了ua的算法,加入了鼠标移动之类的信息,如果有解决方法的欢迎来[pr](https://github.com/wxy1343/aliyunpan/pulls)

```shell
npm install jsdom
```

### 配置refresh_token

```shell
echo "refresh_token: 'xxxxx'"  >  ~/.config/aliyunpan.yaml
```

### 配置账号(可选)

```shell
echo "username: 'xxxxx'"  >  ~/.config/aliyunpan.yaml
echo "password: 'xxxxx'"  >>  ~/.config/aliyunpan.yaml
```

### 配置aria2(可选)

```shell
cat >> ~/.config/aliyunpan.yaml <<EOF
aria2:
  'host': 'http://localhost'
  'port': 6800
  'secret': ''
EOF
```

## 功能介绍

|指令                    |描述                           |
|-----------------------|------------------------------|
|download (d)           |下载文件/文件夹                  |
|ls (dir,l,list)        |列目录                         |
|mv (move)              |移动文件/文件夹                  |
|rm (del,delete)        |删除文件/文件夹                  |
|rename (r)             |重命名文件/文件夹                |
|tree (show,t)          |查看文件树                      |
|upload (u)             |上传文件/文件夹                  |
|share (s)              |分享文件                        |
|mkdir (m)              |创建文件夹                      |
|cat (c)                |显示文件内容                    |
|tui                    |文本用户界面                    |
|search                 |搜索文件/文件夹                 |
|sync                   |同步文件夹                     |
|token (r,refresh_token)|查看refresh_token             |

## 使用指南

* 查看帮助

```shell
aliyunpan-cli -h
```

<details>
    <summary>查看详情</summary>
    <table>
        <tbody>
            <tr>
                <td>参数</td>
                <td>描述</td>
            </tr>
            <tr>
                <td>-h, --help</td>
                <td>查看帮助</td>
            </tr>
            <tr>
                <td>--version</td>
                <td>查看版本</td>
            </tr>
            <tr>
                <td>-c, --config-file</td>
                <td>指定配置文件</td>
            </tr>
            <tr>
                <td>-t, --refresh-token</td>
                <td>指定REFRESH_TOKEN</td>
            </tr>
            <tr>
                <td>-u, --username</td>
                <td>指定账号</td>
            </tr>
            <tr>
                <td>-p, --password</td>
                <td>指定密码</td>
            </tr>
            <tr>
                <td>-d, --depth</td>
                <td>文件递归深度</td>
            </tr>
            <tr>
                <td>-T, --timeout</td>
                <td>请求超时时间(秒)</td>
            </tr>
            <tr>
                <td>-id, --drive-id</td>
                <td>指定drive_id</td>
            </tr>
            <tr>
                <td>-a, --album</td>
                <td>是否访问相册</td>
            </tr>
            <tr>
                <td>-s, --share-id</td>
                <td>指定分享id</td>
            </tr>
            <tr>
                <td>-sp, --share-pwd</td>
                <td>指定分享密码</td>
            </tr>
            <tr>
                <td>-f, --filter-file</td>
                <td>过滤文件(多个)</td>
            </tr>
            <tr>
                <td>-w, --whitelist</td>
                <td>使用白名单过滤文件</td>
            </tr>
            <tr>
                <td>-m, --match</td>
                <td>指定使用正则匹配文件</td>
            </tr>
        </tbody>
    </table>
</details>

* 查看指令参数

```shell
aliyunpan-cli COMMAND -h
```

<details>
    <summary>查看详情</summary>
    <table>
        <tbody>
            <tr>
                <td>指令</td>
                <td>参数</td>
                <td>描述</td>
            </tr>
            <tr>
                <td>download</td>
                <td>-p, --file</td>
                <td>选择文件(多个)</td>
            </tr>
            <tr>
                <td>download</td>
                <td>-s, --share</td>
                <td>指定分享的序列文件</td>
            </tr>
            <tr>
                <td>download</td>
                <td>-cs, --chunk-size</td>
                <td>分块大小(字节)</td>
            </tr> 
            <tr>
                <td>download</td>
                <td>-a, --aria2</td>
                <td>发送到aria2</td>
            </tr> 
            <tr>
                <td>ls,search</td>
                <td>-l</td>
                <td>查看详情</td>
            </tr>        
            <tr>
                <td>share</td>
                <td>-p, --file</td>
                <td>指定文件(多个)</td>
            </tr> 
            <tr>
                <td>share</td>
                <td>-f, --file-id</td>
                <td>指定file_id(多个)</td>
            </tr>        
            <tr>
                <td>share</td>
                <td>-t, --expire-sec</td>
                <td>分享过期时间(秒)，默认最大14400</td>
            </tr>
            <tr>
                <td>share</td>
                <td>-l, --share-link</td>
                <td>输出分享链接</td>
            </tr>        
            <tr>
                <td>share</td>
                <td>-d, --download-link</td>
                <td>输出下载链接</td>
            </tr>        
            <tr>
                <td>share</td>
                <td>-s, --save</td>
                <td>保存序列文件到云盘和本地</td>
            </tr>        
            <tr>
                <td>share</td>
                <td>-S, --share-official</td>
                <td>官方分享功能(需要账号支持)</td>
            </tr>         
            <tr>
                <td>upload</td>
                <td>-p, --file</td>
                <td>选择文件(多个)</td>
            </tr>        
            <tr>
                <td>upload,sync</td>
                <td>-t, --time-out</td>
                <td>分块上传超时时间(秒)</td>
            </tr>        
            <tr>
                <td>upload,sync</td>
                <td>-r, --retry</td>
                <td>上传失败重试次数</td>
            </tr>        
            <tr>
                <td>upload</td>
                <td>-f, --force</td>
                <td>强制覆盖文件</td>
            </tr>
            <tr>
                <td>upload</td>
                <td>-s, --share</td>
                <td>指定分享的序列文件</td>
            </tr> 
            <tr>
                <td>upload,sync</td>
                <td>-cs, --chunk-size</td>
                <td>分块大小(字节)</td>
            </tr> 
            <tr>
                <td>upload</td>
                <td>-c</td>
                <td>断点续传</td>
            </tr>        
            <tr>
                <td>cat</td>
                <td>-e, --encoding</td>
                <td>文件编码</td>
            </tr>        
            <tr>
                <td>sync</td>
                <td>-st, --sync-time</td>
                <td>同步间隔时间</td>
            </tr>        
            <tr>
                <td>sync</td>
                <td>--no-delete, -n</td>
                <td>不删除(云盘/本地)文件(默认)</td>
            </tr>        
            <tr>
                <td>sync</td>
                <td>-d, --delete</td>
                <td>允许删除(云盘/本地)文件</td>
            </tr>         
            <tr>
                <td>sync</td>
                <td>-l, --local</td>
                <td>同步云盘文件到本地</td>
            </tr>        
            <tr>
                <td>token</td>
                <td>--refresh, -r</td>
                <td>刷新配置文件token</td>
            </tr>        
            <tr>
                <td>token</td>
                <td>--refresh-time, -t</td>
                <td>自动刷新token间隔时间(秒)</td>
            </tr>        
            <tr>
                <td>token</td>
                <td>--change, -c</td>
                <td>设置新的refresh_token</td>
            </tr>
        </tbody>
    </table>
</details>

### 断点续传

* 将文件分成多块顺序上传
* 文件上传进度保存在当前目录下的tasks.yaml
* 格式
  ```yaml
  文件sha1:
    path: 绝对路径
    upload_id: 上传id
    file_id: 文件id
    chunk_size: 分块大小
    part_number: 最后上传的分块编号
  ```
* 文件未上传成功时，CTRL+C会自动保存
* 断点续传需带上参数-c

### 分享

* 由于官方修改秒传接口导致该功能失效
* 暂时采用在秒传链接中加入直链的方法用以获取proof_code
* 分享秒传文件时需要通过直链获取文件随机8字节，导致速度较慢
* 由于直链的局限，秒传链接有效期为4小时

1.分享链接格式

```
aliyunpan://文件名|sha1|url_base64|文件大小|相对路径
```

例如

* 以下秒传链接均已失效，仅供参考

```
aliyunpan://示例文件.txt|F61851825609372B3D7F802E600B35A497CFC38E|url_base64|24|root
```

2.文件分享

```shell
aliyunpan-cli share 示例文件.txt 
```

导入

```shell
aliyunpan-cli upload "aliyunpan://示例文件.txt|F61851825609372B3D7F802E600B35A497CFC38E|url_base64|24|root"
```

3.文件夹分享

```shell
aliyunpan-cli share 示例文件夹
```

导入

```shell
aliyunpan-cli upload -s "aliyunpan://示例文件夹|80E7E25109D4246653B600FDFEDD8D8B0D97E517|url_base64|970|root"
```

### TUI按键指南

* 显示菜单(ctrl+x)
* 退出(ctrl+c)
* 切换标签(↑↓←→,kjhl,TAB)

### 环境变量

```ALIYUNPAN_CONF``` 配置文件路径  
```ALIYUNPAN_ROOT``` 根目录(log和tasks输出路径)

## 致谢

感谢 [zhjc1124/aliyundrive](https://github.com/zhjc1124/aliyundrive) 的登录接口参考
