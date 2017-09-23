#!/bin/bash

#cd `dirname $0`


baseDir=$(cd "$(dirname "$0")"; pwd)
echo $baseDir

V_TODAY_YYYY_MM_DD=`date --date="$V_TODAY_YYYYMMDD" +%Y-%m-%d`
V_YESTERDAY=`date --date="${V_TODAY_YYYY_MM_DD} -1 day" +%Y-%m-%d`

echo "littleboy_user_remains_month.sh begins to run, year=${V_PARYEAR},month=${V_PARMONTH},day=${V_PARDAY}"
sh -x ./littleboy_user_remains_month.sh ${V_TODAY_YYYY_MM_DD}
echo "littleboy_user_remains_month.sh end to run, year=${V_PARYEAR},month=${V_PARMONTH},day=${V_PARDAY}"

line_num=`$HADOOP_HOME/bin/hadoop fs -du -s /user/fbi/manhattan_dm/littleboy_user_remains_month/$V_PARYEAR/$V_PARMONTH/$V_PARDAY/|awk '{print $1}'`

if [ $line_num -eq 0 ]
then
    echo "/user/fbi/manhattan_dm/littleboy_user_remains_month/$V_PARYEAR/$V_PARMONTH/$V_PARDAY/ is empty"
else
   echo "littleboy_user_remains_month.sh success"
   $HADOOP_HOME/bin/hadoop fs -touchz /user/fbi/manhattan_dm/littleboy_user_remains_month/$V_PARYEAR/$V_PARMONTH/$V_PARDAY/_SUCCESS
fi
sh -x ./sqoop_export.sh $V_YESTERDAY littleboy_user_remains statdate,cycle_type,city_id,type,order_money,channel_id,start_date,end_date,group_num,user_remains_num,relate_date,province_code,province_name /user/fbi/manhattan_dm/littleboy_user_remains_month/$V_PARYEAR/$V_PARMONTH/$V_PARDAY/
