## gunicorn


### 1. gunicorn 简要介绍

gunicorn 官网文档：[http://docs.gunicorn.org/](http://docs.gunicorn.org/)

使用 pip 安装 gunicorn

    pip install gunicorn

gunicorn 安装完成之后会有三个命令可供使用

    gunicorn
    gunicorn_django
    gunicorn_paster



`gunicorn_django` 适用于 django1.4 之前的版本，django1.4 及以后的版本推荐使用 `gunicorn`


我们在这里仅介绍 `gunicorn_django` 的用法，其用法为：

    gunicorn_django [OPTIONS] [SETTINGS_PATH]
    

简单示例：

    gunicorn_django --bind=0.0.0.0:6000 /home/python/dataeye/settings/dev_settings.py


上面的 `--bind` 为其中的一个配置，具体可通过 `gunicorn -h` 进行查看。此处是在命令行中进行配置，也可以在配置文件中进行相关的配置，在这里使用配置文件进行配置。


### 2. 配置文件

参考这里：[http://docs.gunicorn.org/en/stable/settings.html](http://docs.gunicorn.org/en/stable/settings.html)


配置文件 `gunicorn_config.py`：

```python

#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import multiprocessing

PWD_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PWD_DIR)
# os.environ['DJANGO_SETTINGS_MODULE'] = 'settings.dev_settings'

bind = "127.0.0.1:6000"
django_settings = "settings.dev_settings"   # 和上面注释掉的添加 DJANGO_SETTINGS_MODULE 环境变量的作用一样，两者取其一即可
workers = multiprocessing.cpu_count() * 2 + 1


def when_ready(server):
    print 'server is start.'


def on_exit(server):
    print '\nserver is stop.'

```

运行：

    gunicorn_django -c /home/python/dataeye/gunicorn_config.py


#### 参考：

- [http://www.cnblogs.com/ArtsCrafts/p/gunicorn.html](http://www.cnblogs.com/ArtsCrafts/p/gunicorn.html)