#!/bin/sh`
if [ $# -eq 1 ];then
   V_DATE=$1
else
  V_DATE=`date +%Y-%m-%d`
fi
 echo $V_DATE
 predate=`date --date "${V_DATE} -1 day" "+%Y/%m/%d"`
 echo $predate
V_PARYEAR=`date --date="$V_DATE-1 day" +%Y`
V_PARMONTH=`date --date="$V_DATE-1 day" +%m`
V_PARDAY=`date --date="$V_DATE-1 day" +%d`
V_YESTERDAY=`date --date="$V_DATE-1 day" +%Y%m%d`
V_YESTERDAY_0=`date --date="$V_DATE-1 day" +%Y-%m-%d`
delta=$((`date --date="$V_YESTERDAY" +%u`-1))
V_MONDAY=`date --date="$V_YESTERDAY-${delta} day" +%Y%m%d`
V_MONDAY_0=`date --date="$V_YESTERDAY-${delta} day" +%Y-%m-%d`
hive -e "

use manhattan_dm;
set hive.exec.parallel=true;

add jar ./hiveudf.jar;
create temporary function last_day as 'hive.udf.LastDay';
create temporary function get_month as 'hive.udf.MonthDiff';
alter table littleboy_user_remains_month add if not exists partition(year='$V_PARYEAR',month='$V_PARMONTH',day='$V_PARDAY') location '$V_PARYEAR/$V_PARMONTH/$V_PARDAY';
insert overwrite table littleboy_user_remains_month partition(year='$V_PARYEAR',month='$V_PARMONTH',day='$V_PARDAY')

select
  0 as id,
  '${V_YESTERDAY_0}' stat_date, -- 日期
  cycle_type, --统计类型
  city_id, --城市
  type, --类型
  order_money, --金额 
  channel_id, --渠道
  start_date, --开始日期
  end_date, --结束日期
  group_num, --第几组
  user_remains_num, --用户存留数
  relate_date, -- 对比计算周期的结束日期
  province_code, --省份
  province_name --省份名称
from
(
  select
      2 as cycle_type, --统计类型
      city_id, --城市
      type, --类型
      order_money, --金额 
      channel_id, --渠道
      start_date, --开始日期
      end_date, --结束日期
      group_num, --第几组
      sum(case when remains_user_id is not null then 1 else 0 end) user_remains_num, --用户存留数
      concat_ws('-','$V_PARYEAR','$V_PARMONTH','01') relate_date, -- 对比计算周期的结束日期
      province_code,
      province_name
  from
  (
    select
      t1.user_id user_id,
      t1.city_id,
      type,
      order_money,
      channel_id,
      start_date,
      end_date,
      get_month(start_date,concat_ws('-','$V_PARYEAR','$V_PARMONTH','01')) group_num,
      t2.user_id as remains_user_id,
      coalesce(province_code,0) province_code,
      coalesce(province_name,'未知') province_name
    from
    (
      select
        user_id,
        city_id,
        channel_id,
        type,
        order_money,
        concat_ws('-',substr(create_time,1,7),'01') start_date,
        last_day(to_date(create_time)) end_date
      from manhattan_dw.dw_littleboy_user_first_order
      where concat(year,month,day)='${V_YESTERDAY}'
    ) t1
    left outer join
    (
      select
        user_id
      from manhattan_dw.dw_littleboy_order_base
      where concat_ws('-',year,month,day) between concat_ws('-','$V_PARYEAR','$V_PARMONTH','01') and '${V_YESTERDAY_0}'
      and status=1
      group by user_id
    ) t2
    on (t1.user_id=t2.user_id)
    left outer join
    (
        select
            city_id,
            province_code,
            province_name
        from manhattan_ods.city_province_info
    ) t3
    on (t1.city_id=t3.city_id)
  ) t4
  group by city_id,type,order_money,channel_id,start_date,end_date,group_num,province_code,province_name
) t5
"
