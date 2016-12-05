## BI web 部署文档

**此文档主要为补充文档，为安装完基本软件（mysql mysql-devel python-devel 等）和安装完 requirements.txt 之后的一个补充**

### 1. /root 目录介绍：

文件/目录 | 介绍
--- | ---
deploy.sh | BI web 部署脚本，需要更新时可从 /root/python 目录中进行拷贝
media | BI web admin 所使用的 media，需要从旧服务器中拷贝
nodegulp | 压缩 css、js 文件的处理目录，需要从旧服务器中拷贝
node-v4.2.4-linux-x64 | node 安装包解压目录，可从旧服务器中拷贝，也可下载 node 安装包后解压得到
python | 源代码目录，使用 git clone 得到


**注意：**
`node-v4.2.4-linux-x64` 目录拷贝到新服务器之后，需要确认 `bin` 目录结构为下述所示，若 `gulp` 和 `npm` 不是软链接，则删除，手动创建软链接
```
[root@bi-web ~]# ll node-v4.2.4-linux-x64/bin/
total 24128
lrwxrwxrwx 1 root   root         36 Apr 27 18:27 gulp -> ../lib/node_modules/gulp/bin/gulp.js
-rwxrwxr-x 1 zabbix zabbix 24704622 Dec 24 00:46 node
lrwxrwxrwx 1 zabbix zabbix       38 Apr 27 18:27 npm -> ../lib/node_modules/npm/bin/npm-cli.js
[root@bi-web ~]# 
```

### 2. 配置 git

为了在服务器上可以直接使用 git 协议来更新源代码，需要添加服务器上的 ssh key （使用 root 用户执行 `ssh-keygen -t rsa` 生成） 到 gitlab 中。  
BI web 服务器的 ssh key 统一使用 biweb_all 用户进行管理：

1. 以 biweb_all 用户（密码也是 biweb_all）登录 gitlab，然后将新服务器上生成的 ssh key （`cat /root/.ssh/id_rsa.pub`）添加到 ssh key
2. 在 /root 目录下执行 `git clone git@42.62.6.139:bi/python.git` 即可将最新线上代码 clone 到 /root/python 目录中


### 3. 配置 gulp

gulp 用于压缩 css 和 js 文件。在情况紧迫下可将 deploy.sh 中的 gulp 注释并过滤此步骤，暂不使用压缩，后续再打开即可。
1. 需要 nodegulp 目录，最好是从旧服务器中拷贝
2. 添加软链接，以便使用 gulp。需要在/usr/local/bin 下建立软链接
3. 添加环境变量，在 `/root/.bashrc` 文件末尾添加 `export PATH="/usr/local/bin:$PATH"`；最后 `source /root/.bashrc`

```shell
[root@bi-web ~]# ll /usr/local/bin/
total 0
lrwxrwxrwx 1 root root 36 Apr 27 18:26 gulp -> /root/node-v4.2.4-linux-x64/bin/gulp
lrwxrwxrwx 1 root root 36 Apr 27 18:28 node -> /root/node-v4.2.4-linux-x64/bin/node
lrwxrwxrwx 1 root root 35 Apr 27 18:28 npm -> /root/node-v4.2.4-linux-x64/bin/npm
```


### 4. 发送邮件日报

系统中使用 firefox 静默运行，访问日报页面并截图。需要安装：

安装包名称 | 安装命令 | 说明
--- | --- | ---
firefox | yum install firefox | firefox 浏览器
xorg-x11-server-Xvfb | yum install xorg-x11-server-Xvfb | firefox 静默运行所需
中文支持包 | yum groupinstall "Chinese Support" | 服务器需要支持中文，防止日报页面中文乱码
微软雅黑字体 | -- | 安装微软雅黑字体，使日报页面中的微软雅黑字体能够正常显示


#### 如何安装微软雅黑字体（参考 [http://xinzhiwen198941-163-com.iteye.com/blog/2124179](http://xinzhiwen198941-163-com.iteye.com/blog/2124179)）：

1. 从 windows 中（以 win7 为例）`C:\Windows\Fonts\微软雅黑` 拷贝 msyh.ttf 文件到服务器上
2. 在 /usr/share/fonts 目录下新建一个目录（如 msyh）存放微软雅黑字体
3. 将 msyh.ttf 拷贝至 /usr/share/fonts/msyh 中
4. 运行 fc-cache -fv
5. 查看字体 fc-list :lang=zh


### 5.开机自启
rc.local添加

```
/etc/init.d/nginx start
/root/anaconda/bin/supervisord
```
