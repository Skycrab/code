## gitlab 安装与迁移

### 安装 gitlab 参照：

https://about.gitlab.com/downloads/#centos6


### 迁移 gitlab 参照：

http://blog.csdn.net/limingjian/article/details/42126369  
http://mvpxuan.lofter.com/post/230e17_89589c5


#### 备份

    gitlab-rake gitlab:backup:create

会在 /var/opt/gitlab/backups 目录下创建一个 Gitlab 整个的完整部分的备份。

#### 恢复

    gitlab-rake gitlab:backup:restore

#### 迁移

1. 先在新服务器上安装 gitlab
2. 安装后需要达到能够看到登录页面
3. 在原服务器上进行备份，将 /var/opt/gitlab/backups 目录下的备份文件拷贝到新服务器对应的 /var/opt/gitlab/backups 目录下
4. 在新服务器上进行恢复即可