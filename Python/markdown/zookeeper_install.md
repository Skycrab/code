## zookeeper

安装:

    yum remove java
    yum install java-1.8.0-openjdk.x86_64

    wget http://apache.fayea.com/zookeeper/zookeeper-3.4.8/zookeeper-3.4.8.tar.gz

    mkdir /data1/zookeeper1/data /data1/zookeeper1/logs

    echo 1 > /data1/zookeeper1/data/myid

配置文件:
```
# vim conf/zoo.cfg

tickTime=2000

initLimit=5

syncLimit=2

dataDir=/data1/zookeeper1/data

dataLogDir=/data1/zookeeper1/logs

clientPort=2181

server.1=192.168.2.37:2888:3888

server.2=192.168.2.39:2888:3888

server.3=192.168.2.40:2888:3888
```

supervisor监控配置:

```
aetc/supervisor/conf.d
keeper]
command=/root/zookeeper/zookeeper-3.4.8/bin/zkServer.sh start-foreground
directory=/root/
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile = /data1/zk.log
```

