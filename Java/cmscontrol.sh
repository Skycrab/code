
#!/usr/bin/env bash

JAVA_OPTS=" -server -Xms2048M -Xmx2048M -XX:PermSize=128M -XX:MaxPermSize=128M -XX:+UseConcMarkSweepGC -XX:+UseParNewGC -verbose:gc -XX:+PrintGCDetails -XX:+PrintGCDateStamps -XX:+PrintHeapAtGC -Xloggc:/home/xiaoju/data1/gc.log -XX:CMSInitiatingOccupancyFraction=20 -XX:+UseCMSInitiatingOccupancyOnly -XX:+CMSClassUnloadingEnabled -XX:+DisableExplicitGC -XX:+PrintPromotionFailure -XX:+UseCMSCompactAtFullCollection -XX:+UseCompressedOops -XX:ParallelGCThreads=4 -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/home/xiaoju/data1/oom.dump"

function start()
{
nohup java ${JAVA_OPTS} -jar ./fbi-eagle-api.jar 2>/dev/null 1>/dev/null &
}

case $1 in
    "start" )
        start
        ;;
    "*" )
        echo "error params"
        ;;
esac

