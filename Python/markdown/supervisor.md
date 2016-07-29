## supervisor

官网地址：[http://supervisord.org/](http://supervisord.org/)

安装：

    pip install supervisor
    
启动：

    supervisord

##### 1. 在 `/etc/supervisor` 目录中通过 `echo_supervisord_conf > supervisord.conf` 命令来生成 `supervisord.conf` 配置文件，并在文件末尾添加：

```
[include]
files = /etc/supervisor/conf.d/*.conf
```

##### 2. 在 `/etc/supervisor/conf.d` 目录（在 centos 中需要自己手动创建此目录）中添加 `gunicorn.conf` 文件，文件内容如下：

```
[program:gunicorn]
command=/bin/gunicorn_django -c /home/python/dataeye/gunicorn_config.py
directory=/home/python/dataeye
user=root
autostart=true
autorestart=true
redirect_stderr=true
```

此配置文件为 supervisor 监控 gunicorn 进程的配置文件


启动单个被监控进程

```shell
supervisorctl status
supervisorctl start gunicorn
supervisorctl stop gunicorn
```

上面的 `gunicorn` 为配置文件 `[program:gunicorn]` 中的 `gunicorn` （可自定义，标识被监控进程）


重新加载 `supervisor` 配置文件：

    supervisorctl reload