#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 任务类型: py_spark python3
#********************************************************************#
##author:yihaibo
##create time:2021-09-14 19:11:07
##desc:big_tag_version_py3
##remind:请在资源引用中添加需要引用的资源
#********************************************************************#

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
import pyspark.sql.functions as f
import json
import requests
import os
import time
from collections import defaultdict




# dchat发送接口
DCHAT_URL = "http://xxxxxx"
# dchat组id
DCHAR_GROUP_ID = "xxxxxx"

# bigdata版本接口
TAG_VERSION_URL = "http://xxxxxx"


TAG = {
    "fin_passenger_pub": {
        "name": "金融乘客公有域",
        "entityId": 18,
        "tag": "fe.pub_manhattan_passenger_update"
    },
    "fin_user": {
        "name": "金融用户域",
        "entityId": 24,
        "tag": "fe.manhattan_marketing_user_upate"
    },
    "fin_hxz": {
        "name": "金融花小猪域",
        "entityId": 20,
        "tag": "fe.hxz_manhattan_passenger_update"
    }
}




"""
获取标签版本
@parameter entityId: 实体id
    金融乘客公有域实体id：18；
    金融乘客HXZ：20；
    金融用户：24
@parameter featureList: 特征列表
"""
def get_tag_version(entityId, feature_list):
    data = {
        'entityId': entityId,
        'featureList': feature_list
    }
    def ok_check(result):
        if result['success']:
            return True
        else:
            return False
        
    return post_retry(TAG_VERSION_URL, data, ok_check)["data"]


"""
发送dchat消息
@parameter groupId: dchat组
@parameter message: dchat消息
@parameter receiver: dchat接收人
"""
def send_dc_message(groupId, message, receiver):
    def ok_check(result):
        if result['errorCode'] == 0:
            return True
        else:
            return False

    post_retry(DCHAT_URL, {'receiver': receiver, 'message': message, 'groupId': groupId}, ok_check)

def post_retry(url, data, ok_check):
    for retry in range(0,5):
        body = json.dumps(data)
        print("post: retry:{retry}, url:{url}, body:{body}".format(**locals()))
        r = requests.post(url, json=data)
        print(r.content.decode("utf8"))
        result = r.json()
        if ok_check(result):
            return result
        time.sleep(1)
    raise Exception("http访问异常")


"""
执行shell命令
"""
def execute(cmd):
    print("cmd:" + cmd)
    os.system(cmd)



def main():
    # user_type = argv[1]
    user_type = "fin_user"
    if user_type not in TAG:
        raise Exception("user_type:{user_type} not found".format(**locals()))
    tag = TAG[user_type]
    entityId = tag["entityId"]
    name = tag["name"]
    V_YESTERDAY_0 = '${V_YESTERDAY_0}'
    year='${V_PARYEAR}'
    month='${V_PARMONTH}'
    day='${V_PARDAY}'

    
    sql = """
    select
            user_type        as user_type,
            tag_id           as tag_id,
            tag_name         as tag_name,
            tag_define       as tag_define
    from fe.tag_define_metadata_to_manhattan    
    where dt = '${V_YESTERDAY_0}'
    and dimen_type = 0
    and effective = 1
    and user_type = {entityId}
    and tag_name not in ('city_id', 'statdate','duid')
    and hidden=0
    """.format(**locals())
    print("sql:" + sql)
    df = spark.sql(sql)
    df.show()

    # datafrmae数据
    data = [r.asDict() for r in  df.collect()]
    # data = [
    #     {"tag_name": "total_ddpay_pay_num_riskmanage_dm", "tag_difine":"测试"}
    # ]
    feature_list = [row["tag_name"] for row in data]

    version = get_tag_version(entityId, feature_list)

    version_map = {v["featureName"] : v for v in version}

    # 降级信息
    degrad_version_tables = defaultdict(list)
    # data补充版本和表
    for d in data:
        d["is_degrad"] = 0
        d["table_name"] = ""
        d["partition_date"] = ""
        if d["tag_name"] in version_map:
            m = version_map[d["tag_name"]]
            d["table_name"] = m["tableName"]
            d["partition_date"] = m["partitionDate"]
            if m["partitionDate"] < V_YESTERDAY_0:
                d["is_degrad"] = 1
                degrad_version_tables[d["table_name"]].append(d)
            
    print("all version:\n" + json.dumps(data))
    print("degrad_version:\n" + json.dumps(degrad_version_tables))

    message = """标签系统 {name} {V_YESTERDAY_0} 更新成功\n""".format(**locals())
    degrade_message = ""
    # 存在降级信息
    if len(degrad_version_tables) > 0:
        degrade_message += "部分标签已降级，信息如下:\n"
        for table, tags in degrad_version_tables.items():
            degrad_date = tags[0]["partition_date"]
            degrade_message += "表{table} 降级日期 {degrad_date}\n".format(**locals())

    message += degrade_message

    print(message)

    send_dc_message(DCHAR_GROUP_ID, message, "shuaili,haixuan")

    # 保存到hive表
    df2 = spark.createDataFrame(data).repartition(1)

    df2.printSchema()
    df2.show()

    df2.registerTempTable("t1")
    sql = """
    insert overwrite table dm.bigtag_feature_version PARTITION(year='{year}',month='{month}',day='{day}',user_type='{user_type}')
    select tag_id,user_type,tag_name,tag_define,table_name,partition_date,is_degrad from t1
    """.format(**locals())
    print(sql)

    spark.sql(sql)


main()

