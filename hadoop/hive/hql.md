##hive建表 orc压缩

```
alter table opph_order_jdb_policy_kpi
add columns (`spu_id` int COMMENT 'spu_id') CASCADE;
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
  'hdfs://mycluster-tj/user/fbi/manhattan_dm/sign_bill_funnel_transfor'
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
  'hdfs://mycluster-tj/user/fbi/manhattan_dm/opph_order_jdb_policy_kpi'
TBLPROPERTIES (
  'LEVEL'='1',
  'TTL'='180',
  'last_modified_by'='fbi',
  'last_modified_time'='1509508546',
  'transient_lastDdlTime'='1509508546')
```

