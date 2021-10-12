#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 任务类型: py_spark
#********************************************************************#
##author:yihaibo
##create time:2021-08-18 21:05:06
##desc:
##remind:请在资源引用中添加需要引用的资源
#********************************************************************#

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
import pyspark.sql.functions as f
import json

year='$V_PARYEAR'
month='$V_PARMONTH'
day='$V_PARDAY'

spark = SparkSession.builder.appName("test") \
    .getOrCreate()

sql = """
    SELECT
        param['uid'] as uid,
        floor((param['send_time']/1000 - unix_timestamp('${V_YESTERDAY_0} 00:00:00'))/600) as time_interval,
        sum(case when param['msg_event_id']==5 and param['resource_id']=153 and param['business_id']=256 then 1 else 0 end) as rsId_153_bnId_256_exposure_num,
        sum(case when param['msg_event_id']==6 and param['resource_id']=153 and param['business_id']=256 then 1 else 0 end) as rsId_153_bnId_256_click_num,
        sum(case when param['msg_event_id']==5 and param['resource_id']=153 and param['business_id']=260 then 1 else 0 end) as rsId_153_bnId_260_exposure_num,
        sum(case when param['msg_event_id']==6 and param['resource_id']=153 and param['business_id']=260 then 1 else 0 end) as rsId_153_bnId_260_click_num,
        sum(case when param['msg_event_id']==6 and param['resource_id']=259 and param['business_id']=994 then 1 else 0 end) as rsId_259_bnId_994_click_num,
        sum(case when param['msg_event_id']==5 and param['resource_id']=259 and param['business_id']=372 then 1 else 0 end) as rsId_259_bnId_372_exposure_num,
        sum(case when param['msg_event_id']==6 and param['resource_id']=259 and param['business_id']=372 then 1 else 0 end) as rsId_259_bnId_372_click_num
    FROM log
    WHERE concat_ws('-',YEAR, MONTH, DAY) = '${V_YESTERDAY_0}'
    and param['msg_event_id'] in (5, 6) --5曝光6点击
    and cast(param['uid'] as bigint) is not null
    and param['resource_id'] in ('153','63','437','18','249','155','342','235','257','259') --固定资源位
    and param['business_id'] in ('256','260','666','994','372')  --固定业务线
    and floor((param['send_time']/1000 - unix_timestamp('${V_YESTERDAY_0} 00:00:00'))/600)>=0
    and floor((param['send_time']/1000 - unix_timestamp('${V_YESTERDAY_0} 00:00:00'))/600)<=143
    group by param['uid'], floor((param['send_time']/1000 - unix_timestamp('${V_YESTERDAY_0} 00:00:00'))/600)
"""

print(sql)
df2 = spark.sql(sql)
#df2.cache()
#df2.show()

columns = df2.columns
columns.remove("uid")
columns.remove("time_interval")

# 所有指标列合并
df3 = df2.withColumn('data',f.array(columns))

#df3.show(10, False)

# 时间周期合并，时间为key,value为所有指标数组
df4 = df3.groupBy("uid").agg(f.map_from_arrays(f.collect_list("time_interval"), f.collect_list("data")).alias("map"))

#df4.show(10, False)

# udf，时间周期自动往前累加
# def agg(data):
#   f = {}
#   m = data
#   for ci,cn in enumerate(columns):
#     d = {}
#     for i in range(0,144):
#       if i in m:
#          num = m[i][ci]
#       else:
#          num = 0
#       for j in range(0,i):
#          if j in m:
#              num += m[j][ci]
#       d[i]= num
#     f[cn] = d
#   return json.dumps(f)

# udf，优化版，1.时间周期累计使用上个周期 2.最后周期没有数据，资源位剔除
def agg(data):
  f = {}
  m = data
  for ci,cn in enumerate(columns):
    d = {}
    for i in range(0,144):
      if i in m:
         num = m[i][ci]
      else:
         num = 0
      # 补上上一个时间周期
      if i > 0:
        num += d[i-1]
      d[i]= num
    # 最后一个周期都没有数，所有时间周期都没有，剔除掉
    if d[143] > 0:
      f[cn] = d
  return json.dumps(f)


agg_udfs = udf(agg, StringType())

df4 = df4.repartition(1000)

df5 = df4.select("uid", agg_udfs(df4["map"]).alias("data"))

#df5.show(10, False)

df5.registerTempTable("t1")
sql = """
insert overwrite table dm.resource_tenminutes PARTITION(year='{year}',month='{month}',day='{day}')
select uid, data from t1
""".format(year=year, month=month, day=day)

print(sql)

spark.sql(sql)

