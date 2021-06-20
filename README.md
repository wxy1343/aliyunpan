# aliyunpan

---

阿里云盘cli  
环境要求： python 3.7 通过测试  
~~低版本环境运行报错参考~~[~~issue9~~](https://github.com/wxy1343/aliyunpan/issues/9)

## 安装

```shell
git clone https://github.com/wxy1343/aliyunpan --recurse-submodules
```

## 获取refresh_token

![token](https://github.com/wxy1343/aliyunpan/raw/main/token.png)

### 注意

* web端获取的refresh_token暂时无法分享

1. 可以指定账号密码登入
2. 可以通过手机端查找日志获取refresh_token

> /sdcard/Android/data/com.alicloud.databox/files/logs/trace/userId/yunpan/latest.log

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

|指令                 |描述                           |
|--------------------|------------------------------|
|download (d)        |下载文件/文件夹                  |
|ls (dir,l,list)     |列目录                         |
|mv (move)           |移动文件/文件夹                  |
|rm (del,delete)     |删除文件/文件夹                  |
|rename (r)          |重命名文件/文件夹                |
|tree (show,t)       |查看文件树                      |
|upload (u)          |上传文件/文件夹                  |
|share (s)           |分享文件                        |
|mkdir (m)           |创建文件夹                      |
|cat (c)             |显示文件内容                    |
|tui                 |文本用户界面                    |
|search              |搜索文件/文件夹                 |
|sync                |同步文件夹                     |

## 使用指南

* 查看帮助

```shell
python main.py -h
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
                <td>-t</td>
                <td>指定REFRESH_TOKEN</td>
            </tr>
            <tr>
                <td>-u</td>
                <td>指定账号</td>
            </tr>
            <tr>
                <td>-p</td>
                <td>指定密码</td>
            </tr>
            <tr>
                <td>-d, --depth</td>
                <td>文件递归深度</td>
            </tr>
        </tbody>
    </table>
</details>

* 查看指令参数

```shell
python main.py COMMAND -h
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
                <td>-s, share</td>
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
                <td>-s, share</td>
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
                <td>--sync-time</td>
                <td>同步间隔时间</td>
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

1.分享链接格式

```
aliyunpan://文件名|sha1|文件大小|相对路径
```

例如

```
aliyunpan://示例文件.txt|F61851825609372B3D7F802E600B35A497CFC38E|24|root
```

2.文件分享

```shell
python main.py share 示例文件.txt 
```

导入

```shell
python main.py upload "aliyunpan://示例文件.txt|F61851825609372B3D7F802E600B35A497CFC38E|24|root"
```

3.文件夹分享

```shell
python main.py share 示例文件夹
```

导入

```shell
python main.py upload -s "aliyunpan://示例文件夹|80E7E25109D4246653B600FDFEDD8D8B0D97E517|970|root"
```

### TUI按键指南

* 显示菜单(ctrl+x)
* 退出(ctrl+c)
* 切换标签(↑↓←→,kjhl,TAB)

## 致谢

感谢 [zhjc1124/aliyundrive](https://github.com/zhjc1124/aliyundrive) 的登录接口参考
