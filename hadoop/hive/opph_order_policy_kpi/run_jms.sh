#!/bin/bash

#cd `dirname $0`


baseDir=$(cd "$(dirname "$0")"; pwd)
echo $baseDir

V_TODAY_YYYY_MM_DD=`date --date="$V_TODAY_YYYYMMDD" +%Y-%m-%d`
V_YESTERDAY=`date --date="${V_TODAY_YYYY_MM_DD} -1 day" +%Y-%m-%d`

echo "opph_order_policy_kpi.sh begins to run, year=${V_PARYEAR},month=${V_PARMONTH},day=${V_PARDAY}"
sh -x ./opph_order_policy_kpi.sh ${V_TODAY_YYYY_MM_DD}
echo "opph_order_policy_kpi.sh end to run, year=${V_PARYEAR},month=${V_PARMONTH},day=${V_PARDAY}"

line_num=`$HADOOP_HOME/bin/hadoop fs -du -s /user/fbi/manhattan_dm/opph_order_policy_kpi/$V_PARYEAR/$V_PARMONTH/$V_PARDAY/|awk '{print $1}'`

if [ $line_num -eq 0 ]
then
    echo "/user/fbi/manhattan_dm/opph_order_policy_kpi/$V_PARYEAR/$V_PARMONTH/$V_PARDAY/ is empty"
else
   echo "opph_order_policy_kpi.sh success"
   $HADOOP_HOME/bin/hadoop fs -touchz /user/fbi/manhattan_dm/opph_order_policy_kpi/$V_PARYEAR/$V_PARMONTH/$V_PARDAY/_SUCCESS
fi

java -jar ./load-data-tools.jar $V_YESTERDAY 139
java -jar ./load-data-tools.jar $V_YESTERDAY 159

sh -x ./sqoop_export.sh $V_YESTERDAY opph_order_policy_kpi statdate,channel_id,channel_name,inscompany_id,inscompany_name,product_id,product_name,sales_method,sales_method_name,pay_type,pay_type_name,buy_policy_num,buy_user_num,premium_fee,insurant_user_num,total_policy_num,total_premium_fee,total_user_num,total_insurant_user_num,real_premium_fee,channel_premium_fee,total_real_premium_fee,total_channel_premium_fee,spu_id,spu_name,offer_fee,coupon_amount,month_buy_policy_num,month_premium_fee /user/fbi/manhattan_dm/opph_order_policy_kpi/$V_PARYEAR/$V_PARMONTH/$V_PARDAY/
