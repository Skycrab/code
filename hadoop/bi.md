#phoenix

```
create table report_data_100(
    report_id varchar not null,
    statdate varchar not null,
    dim3 varchar not null,
    dim4 varchar not null,
    dim5 varchar not null,
    dim6 varchar not null,
    dim7 varchar not null,
    dim8 varchar not null,
    dim9 varchar not null,
    dim10 varchar not null,
    dim11 varchar not null,
    dim12 varchar not null,
    dim13 varchar not null,
    dim14 varchar not null,
    dim15 varchar not null,
    dim16 varchar not null,
    dim17 varchar not null,
    dim18 varchar not null,
    dim19 varchar not null,
    dim20 varchar not null,
    valueArray double array,
    dimNameArray varchar array,
    constraint pk primary key (report_id,statdate,dim3,dim4,dim5,dim6,dim7,dim8 ,dim9,dim10,dim11,dim12,dim13,dim14,dim15,dim16,dim17,dim18,dim19,dim20)
);

```

cube
```
select max(statdate)  as dim_item_name_1471,
sum(valueArray[1])  as metric_name_1489,
sum(valueArray[9])  as metric_name_1505,
sum(valueArray[10])  as metric_name_1507,
sum(valueArray[11])  as metric_name_1509,
sum(valueArray[12])  as metric_name_1511,
sum(valueArray[13])  as metric_name_1513,
sum(valueArray[12])/sum(valueArray[9]) as metric_name_1515,
sum(valueArray[11])/sum(valueArray[9]) as metric_name_1517
from "fbi:report_data_100" where report_id = '59'
and statdate<='2016-12-27' and statdate>='2016-12-13'
and dim3='-10000' and dim4='-10000' and dim5='-10000' and dim6='-10000'  group by statdate

```

非cube
```
select max(statdate)  as dim_item_name_2367,
sum(valueArray[1])  as metric_name_2405,
sum(valueArray[6])  as metric_name_2415,
sum(valueArray[6]/100) as metric_name_2417,
sum(valueArray[6]/100)/sum(valueArray[5]) as metric_name_2419,
sum(valueArray[2])/sum(valueArray[1]) as metric_name_2421
from "fbi:report_data_100" where report_id = '71' and statdate<='2017-01-03' and statdate>='2016-11-10'  group by statdate
```

```
delete from "fbi:report_data_100" where report_id = '37' and statdate = '2017-02-02'

Scan ready for iteration: {"loadColumnFamiliesOnDemand":null,"startRow":"\\x0037\\x002017-02-02","stopRow":"\\x0037\\x002017-02-02\\x01","batch":-1,"cacheBlocks":true,"totalColumns":0,"maxResultSize":-1,"families":{},"caching":100,"maxVersions":1,"timeRange":[0,1486065955166]}
```

#hive

```
CREATE EXTERNAL TABLE `kpi`(
  `id` bigint COMMENT 'ID',
  `statdate` string COMMENT '日期',
  `city_id` int COMMENT '城市ID',
  `city_name` string COMMENT '城市名称',
  `apply_num` bigint COMMENT '当日申请次数',
  `apply_user_cnt` bigint COMMENT '当日申请人数')
COMMENT 'KPI'
PARTITIONED BY (
  `year` string,
  `month` string,
  `day` string)
ROW FORMAT SERDE
  'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
STORED AS INPUTFORMAT
  'org.autonavi.udf.CustomInputFormat'
OUTPUTFORMAT
  'org.autonavi.udf.CustomHiveOutputFormat'
LOCATION
  'hdfs://mycluster-tj/user/fbi/drip_loan_kpi'
```

```
use test;
alter table fatman_policy_order_kpi add columns
(`inscompany_name` string COMMENT '名称') CASCADE;
alter table fatman_policy_order_kpi add columns
(`is_operating_vehicle_name` string COMMENT '营运车') CASCADE;

```

```
select
    mobile
from
(
    select
        user_info.driver_id,
        user_info.city_id,
        user_info.mobile,
        user_info.cert_id,
        case when load_info.didi_user_id is null then 0 else 1 end as apply_success, --提交申请是否成功，0未成功，1成功
        case when buddy_tracker.tel is not null and buddy_tracker.open_cnt>0 then 1 else 0 end as home_open, --是否打开营销页面，0未打开，1打开
        case when buddy_tracker.tel is not null and buddy_tracker.apply_cnt>0 then 1 else 0 end as apply_click --是否点击申请，0未点击，1点击
    from
    (
        select
            *
        from
        (
            select
                driver_id,
                city_id,
                mobile,
                cert_id
            from manhattan_ods.drip_loan_white_list where concat_ws('-',year,month,day)='2017-01-10'
            and provider='wangshang'
            and city_id in (${city_id})
        )white_list
        left outer join
        (
            select
                driver_id as base_driver_id
            from manhattan_dw.dw_driver_loan_base_info_result
            where concat_ws('-',year,month,day)==date_sub(concat_ws('-',cast(year('${start_date}') as string),cast(month('${start_date}') as string),'01'),1)
        )base_info
        on(white_list.driver_id=base_info.base_driver_id)
        where base_info.base_driver_id is not null
    )user_info
    left outer join
    (
        select
            didi_user_id
        from manhattan_ods.drip_loan_tbl_loan_info
        where concat_ws('-',year,month,day)='${start_date}' and
        apply_date<='${start_date}' group by didi_user_id
    )load_info
    on(user_info.driver_id=load_info.didi_user_id)
    left outer join
    (
        select
            attrs['tel'] as tel,
            sum(case when eventid='buddy_home_biopen' then 1 else 0 end) as open_cnt, --打开首页次数
            sum(case when eventid='manh-buddy-toalipay-apply' then 1 else 0 end) as apply_cnt --点击申请次数
        from manhattan_ods.ods_buddy_tracker
        where concat_ws('-',year,month,day) between '2016-08-23' and '${start_date}'
        group by attrs['tel']
    )buddy_tracker
    on(user_info.mobile=buddy_tracker.tel)
) t1
where apply_success in (${apply_success})
and home_open in (${home_open})
and apply_click in (${apply_click})
group by mobile
```

#mysql

```
 CREATE TABLE `fatman_order_status` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT COMMENT 'id',
  `statdate` date NOT NULL DEFAULT '1971-01-01' COMMENT '日期',
  `province_code` varchar(50) COLLATE utf8_bin NOT NULL DEFAULT '-1' COMMENT '省份id',
  `cityid` int(11) NOT NULL DEFAULT '0' COMMENT '城市id',
  `inscompany_code` varchar(100) COLLATE utf8_bin NOT NULL DEFAULT '' COMMENT '承保商',
  `vehicle_num` bigint(20) NOT NULL DEFAULT '0' COMMENT '车辆数',
  `order_num` bigint(20) NOT NULL DEFAULT '0' COMMENT '订单数',
  `status` int(11) NOT NULL DEFAULT '0' COMMENT '订单状态',
  `is_operating_vehicle` varchar(20) COLLATE utf8_bin NOT NULL DEFAULT '0' COMMENT '是否营运车，0为私家车，1为营运车',
  PRIMARY KEY (`id`),
  KEY `idx_statdate` (`statdate`),
  KEY `idx_cityid` (`cityid`),
  KEY `idx_province_code` (`province_code`),
  KEY `idx_inscompany_code` (`inscompany_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin COMMENT='状态报表'
```

```
alter table `fatman_order_status`
add `status_name` varchar(30) NOT NULL DEFAULT '' COMMENT '订单状态名称',
add `is_operating_vehicle_name` varchar(50) NOT NULL DEFAULT '' COMMENT '使用性质名称';
```

#小技巧

全量表根据create_time分发分区

```
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

#drip_loan_loan_repay_plan全量表,2017-01-21是拉取时间,create_time是记录创建时间
#根据create_time分发到hive分区

hive -e "
use manhattan_ods;
set hive.exec.parallel=true;
set hive.support.quoted.identifiers=none;

alter table drip_loan_loan_repay_plan add if not exists partition(year='$V_PARYEAR',month='$V_PARMONTH',day='$V_PARDAY') location '$V_PARYEAR/$V_PARMONTH/$V_PARDAY';
insert overwrite table drip_loan_loan_repay_plan partition(year='$V_PARYEAR',month='$V_PARMONTH',day='$V_PARDAY')

select
    `(day)?+.+`
from
(
    select
        `(month)?+.+`
    from
    (
        SELECT
            `(year)?+.+`
        from manhattan_ods.drip_loan_loan_repay_plan where concat(year,month,day)='20170121' and create_time<'${V_YESTERDAY_0} 23:59:59'
    )t1
)t2;


"
```








