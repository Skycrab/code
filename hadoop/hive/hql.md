##hive建表 orc压缩

```
alter table opph_order_jdb_policy_kpi
add columns (`spu_id` int COMMENT 'spu_id') CASCADE;
```
```
desc formatted white_list_test partition (year='2017',month='07',day='')
```

```
REATE EXTERNAL TABLE `sign_bill_funnel_transfor`(
  `id` bigint COMMENT 'ID',
  `statdate` string COMMENT '日期',
  `funds_channel_id` string COMMENT '渠道',
  `funds_channel_id_name` string COMMENT '渠道名称 3001众网 3002网商',
  `risk_level` string COMMENT '风险级别',
  `risk_level_name` string COMMENT '风险级别名称',
  `city_id` int COMMENT '城市ID',
  `city_name` string COMMENT '城市名称',
  `open_user_cnt` bigint COMMENT '开放白名单人数',
  `click12_user_cnt` bigint COMMENT '点击12宫格人数',
  `mark_user_cnt` bigint COMMENT '营销页面人数',
  `apply_loan_user_cnt` bigint COMMENT '申请借款人数',
  `apply_loan_pass_user_cnt` bigint COMMENT '申请通过人数',
  `use_loan_money_user_cnt` bigint COMMENT '支用人数',
  `repayment_user_cnt` bigint COMMENT '还款人数',
  `overdue_money_user_cnt` bigint COMMENT '累计逾期人数',
  `current_delay_user_cnt` bigint COMMENT '当前逾期人数',
  `current_delay_more_30_day_user_cnt` bigint COMMENT '当前逾期30天人数',
  `current_delay_more_60_day_user_cnt` bigint COMMENT '当前逾期60天人数',
  `open_time` string COMMENT '开通时间',
  `open_time_name` string COMMENT '开通时间名称',
  `use_loan_money_total` bigint COMMENT '累计支用金额')
COMMENT '信用付漏斗转化分析'
PARTITIONED BY (
  `year` string COMMENT '年',
  `month` string COMMENT '月',
  `day` string COMMENT '日')
ROW FORMAT SERDE
  'org.apache.hadoop.hive.ql.io.orc.OrcSerde'
STORED AS INPUTFORMAT
  'org.apache.hadoop.hive.ql.io.orc.OrcInputFormat'
OUTPUTFORMAT
  'org.apache.hadoop.hive.ql.io.orc.OrcOutputFormat'
LOCATION
  'hdfs://sign_bill_funnel_transfor'
TBLPROPERTIES (
  'LEVEL'='1',
  'TTL'='60')
```

##hive 普通格式建表

```
CREATE EXTERNAL TABLE `opph_order_jdb_policy_kpi`(
  `id` int COMMENT 'ID',
  `statdate` string COMMENT '日期',
  `channel_id` string COMMENT '渠道编码',
  `channel_name` string COMMENT '渠道名称',
  `inscompany_id` string COMMENT '保险公司编码',
  `inscompany_name` string COMMENT '保险公司名称',
  `sales_method` bigint COMMENT '销售方式 1为赠险,2为直购',
  `sales_method_name` string COMMENT '销售方式名称',
  `buy_policy_num` bigint COMMENT '当日保单数',
  `buy_user_num` bigint COMMENT '当日保单保费金额',
  `premium_fee` bigint COMMENT '累计线索数',
  `total_policy_num` bigint COMMENT '累计保单数',
  `total_user_num` bigint COMMENT '累计保单人数',
  `total_premium_fee` bigint COMMENT '累计保单保费金额',
  `spu_id` int COMMENT 'spu_id',
  `spu_name` string COMMENT 'spu名称',
  `insurant_relation` int COMMENT '被保人和投保人关系1：自己，2：配偶，3：子女',
  `insurant_relation_name` string COMMENT '被保人和投保人关系')
COMMENT '接单保KPI'
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
  'hdfs://opph_order_jdb_policy_kpi'
TBLPROPERTIES (
  'LEVEL'='1',
  'TTL'='180',
  'last_modified_by'='fbi',
  'last_modified_time'='1509508546',
  'transient_lastDdlTime'='1509508546')
```

###orc压缩
新建orc表
```
USE xxx_ods;
CREATE EXTERNAL TABLE tmp_orc LIKE tmp;
ALTER TABLE tmp_orc SET FILEFORMAT ORC;
ALTER TABLE tmp_orc SET LOCATION 'hdfs://tmp_orc';
```
创建目录,增加分区
```
hadoop fs -mkdir -p /user/xiaoju/data/bi/beatles_ods/beatles_strategy_hive_single_route_rank_tmp_orc/2016/06/19/00

use xxx_ods;
alter table tmp_orc add if not exists partition(year='2016',month='06',day='19',hour='00') location '/tmp_orc/2016/06/19/00';
```

插入数据
```
set hive.exec.dynamic.partition=true;
set hive.exec.dynamic.partition.mode=nostrict;
set mapreduce.job.queuename=root.jichupingtaibu-dashujujiagoubu.offline;
set hive.exec.max.created.files=1000000;
set hive.exec.max.dynamic.partitions=1000;
set hive.exec.max.dynamic.partitions.pernode=1000;
set mapreduce.map.memory.mb=4096;
set mapreduce.map.java.opts=-Xmx3072m;
set mapreduce.reduce.java.opts=-Xmx6144m;
set mapreduce.map.memory.mb=4096;
set mapreduce.reduce.memory.mb=8192;
set yarn.scheduler.minimum-allocation-mb=4096;
set yarn.scheduler.maximum-allocation-mb=5120;

USE xx_ods;
INSERT OVERWRITE TABLE tmp_orc PARTITION(year,month,day,hour)
SELECT * FROM tmp where concat(year,month,day,hour) between '2016061900' and '2016062023' DISTRIBUTE BY rand();

```
```
ALTER TABLE dwd_fatman_quotation_errmessage_category partition(year='2017',month='01',day='31') SET FILEFORMAT ORC;
ALTER TABLE manhattan_dw.dwd_fatman_quotation_errmessage_category SET FILEFORMAT ORC;
hadoop fs -chown -R dw_online:route_rank /route_rank

```
