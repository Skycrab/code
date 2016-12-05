#数据库分表介绍

### 1.方案

使用开源kingshard(https://github.com/flike/kingshard) 做mysql proxy

### 2.环境搭建
    - 安装golang

        ```
        # 下载go1.6
        wget http://www.golangtc.com/static/go/1.6/go1.6.linux-amd64.tar.gz
        # 解压到/opt
        tar -xvf  go1.6.linux-amd64.tar.gz -C /opt

        # vi /etc/profile
        export GOROOT=/opt/go
        export PATH=$PATH:$GOROOT/bin
        export GOARCH=amd64
        export GOOS=linux

        source /etc/profile

        # 校验go安装是否正确
        go version
        ```

    - 安装kingshard

        参考 https://github.com/flike/kingshard/blob/master/doc/KingDoc/kingshard_install_document.md

    - 修改diango配置文件



