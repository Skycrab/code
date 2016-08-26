#!/bin/bash

work_home=/data/bi
echo `date`

count=`ps -ef |grep /data/bi/clientids/00001/shell/luo.py |grep -v "grep" |wc -l`
if [ 0 == $count ];then
    echo "start"
    /usr/bin/python /data/bi/clientids/00001/shell/luo.py b >> /data/bi/clientids/00001/log/cron_00001.log 2>&1
    echo -n "end "
    echo `date`
else
    echo "process already exist"
fi

echo '-------------------------------'
