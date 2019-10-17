
#!/bin/bash
#############################################
## main
## 以托管方式, 启动服务
## control.sh脚本, 必须实现start方法
#############################################
workspace=$(cd $(dirname $0) && pwd -P)
cd $workspace

STDOUT_FILE=/home/xiaoju/data1/start-server.log
LIB_DIR=$workspace/lib
LIB_JARS=`ls $LIB_DIR|grep .jar|awk '{print "'$LIB_DIR'/"$0}'|tr "\n" ":"`
CONFIG_DIR=$workspace/config


#jvm
export JAVA_HOME=/usr/local/jdk1.8.0_65
export JAVA_BASE_OPTS=" -Djava.awt.headless=true -Dfile.encoding=UTF-8 -DLOG_DIR=/home/xiaoju/data1 -Denv=qa"
export JAVA_MEM_OPTS=" -server -Xms6g -Xmx6g -Xmn3g -XX:MetaspaceSize=128m -Xss256K "
export JAVA_GC_OPTS=" -XX:+DisableExplicitGC -XX:+UseG1GC -verbose:gc -Xloggc:/home/xiaoju/data1/gc.log -XX:+PrintGCDetails -XX:+PrintGCDateStamps "


action=$1
case $action in
    "start" )
        # 启动服务, 以前台方式启动, 否则无法托管, 注意app和conf中是否有""出现, 保证脚本的正确性
        exec $JAVA_HOME/bin/java ${JAVA_MEM_OPTS} ${JAVA_BASE_OPTS} ${JAVA_GC_OPTS} -classpath $CONFIG_DIR:$LIB_JARS ServerApplication >> $STDOUT_FILE 2>&1
        ;;
    * )
        # 非法命令, 已非0码退出
        echo "unknown command"
        exit 1
        ;;
 esac


