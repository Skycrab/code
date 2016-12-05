# coding=utf8

from __future__ import division
import os
import json
import chardet
import decimal
import operator
import itertools
import functools
import traceback
import subprocess
import time
import datetime
from collections import defaultdict
from dateutil.relativedelta import relativedelta

import torndb
import MySQLdb
from django.http import HttpResponse
from django.conf import settings

import const
from log import logger


errcode = {
    1: "用户名密码有误",
    2: "缺少参数",
    3: "有多余参数",
    4: "数据不存在",
    5: "数据查询错误",
    6: "未授权",
    16: "数据库约束错误",
    32: "验证码错误",
    33: "网络错误",
    34: "请重试",
    35: "验证码发送太快",
    48: "数据格式错误",
    500: "未知错误",
}


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, datetime.time):
            return obj.strftime('%H:%M')
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def json_success(result):
    data = {"err": 0, "errmsg": "", "result": result}
    return json.dumps(data, cls=JsonEncoder)


def json_failed(code):
    assert code in errcode
    data = {"err": code, "errmsg": errcode[code], "result": ""}
    return json.dumps(data, cls=JsonEncoder)


def json_ret(code):
    if code == 0:
        return json_success("")
    else:
        return json_failed(code)


class cached_property(object):
    """ A property that is only computed once per instance and then replaces
        itself with an ordinary attribute. Deleting the attribute resets the
        property. """

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None: return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


def try_cache(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print("[********************************]")
            err = "{0}\n{1}".format(str(e), traceback.format_exc())
            print(err)
            print("[********************************]")
            return HttpResponse(err)
    return wrapper


def cache_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err = "{0}\n{1}".format(str(e), traceback.format_exc())
            logger.error(err)
            if settings.DEBUG:
                print("[********************************]")
                print(err)
                print("[********************************]")
                return HttpResponse(err)
            else:
                code = e.args[0]
                if isinstance(code, int) and code in errcode:
                    return HttpResponse(json_failed(code))
                else:
                    return HttpResponse(json_failed(500))
    return wrapper


def insert_default_data(start, end, result):
    tmp = start
    d = []
    d.append(tmp)
    while tmp < end:
        tmp = tmp + datetime.timedelta(days=1)
        d.append(tmp)
    for k, v in enumerate(d):
        if v not in result['day']:
            result['day'].insert(k, v)
            for result_k in result.keys():
                if result_k != 'day':
                    result[result_k].insert(k, const.DEFAULT_VALUE)


def keep_time_continue(func):
    def wrapper(*args, **kwargs):
        self = args[0]
        result = func(*args, **kwargs)
        if self.start and self.end:
            start=datetime.datetime(*time.strptime(self.start, '%Y-%m-%d')[:3]).date()
            end=datetime.datetime(*time.strptime(self.end, '%Y-%m-%d')[:3]).date()
            insert_default_data(start, end, result)
        elif self.short:
            if self.short == const.YESTERDAY:
                yesterday = get_yesterday()
                if yesterday not in result['day']:
                    result['day'].append(yesterday)
                    for result_k in result.keys():
                        if result_k != 'day':
                            result[result_k].append(const.DEFAULT_VALUE)
            elif self.short == const.TEN_DAYS_AGO:
                start = get_ten_days_ago()
                end = get_yesterday()
                insert_default_data(start, end, result)
            elif self.short == const.CURRENT_MONTH:
                start = get_current_month_one_day()
                end = get_yesterday()
                insert_default_data(start, end, result)
            elif self.short == const.LAST_MONTH:
                start = get_last_month_one_day()
                end = get_last_month_last_day()
                insert_default_data(start, end, result)
            else:
                raise ValueError(2)
        return result
    return wrapper


class DummyModel(object):
    def __init__(self, refer):
        self.refer = refer

    def __getattr__(self, name):
        try:
            return getattr(self.refer, name)
        except AttributeError:
            return 0


def result_merge(*fields, **kwargs):
    """多条记录缺失匹配(组合成同一条记录)
    result_merge("snid", None)
    """
    must = kwargs.get("must", ["gameid", "ds"])

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            assert isinstance(result, dict)
            self = args[0]
            values = []
            # 按主表排序
            for i, model in enumerate(self.table_list):
                name = model.__name__
                i = 0 if i==0 else i - 1
                check = list(must)
                if fields[i] is not None:
                    check.append(fields[i])
                vv = sorted(result[name], key=lambda m: [operator.attrgetter(c)(m) for c in check])
                values.append((check, name, vv))

            master_check, name, masters = values[0]
            total = len(values) - 1
            for i, master in enumerate(masters):
                master_value = {f: getattr(master, f) for f in master_check}
                for j in range(1, total):
                    check, name, models = values[j]
                    try:
                        model = models[i]
                    except IndexError:
                        models.insert(i, DummyModel(master))
                        continue
                    flag = all(getattr(model, f) == master_value[f] for f in check)
                    if not flag:
                        models.insert(i, DummyModel(master))

            #
            for _, name, models in values:
                result[name] = models

            return result
        return wrapper
    return decorator


def get_date_from_string(date_str):
    """将字符串转化成日期序列"""
    return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()


def timestamp(date):
    """convert date or datetime to timestamp"""
    return int(time.mktime(date.timetuple()))


def todate(date):
    """date string to datetime.date"""
    return datetime.datetime.strptime(date, "%Y-%m-%d").date()


def date_delta(date, delta=1):
    """"日期间隔"""
    if delta >= 0:
        new = date + datetime.timedelta(delta)
    else:
        new = date - datetime.timedelta(-delta)

    return new.strftime("%Y-%m-%d"), int(time.mktime(new.timetuple()))


def get_percent_str(a, b):
    """获取百分比字符串"""
    try:
        r = float(a) / b
    except ZeroDivisionError:
        return "0%"
    else:
        return "%.2f%%" % (r * 100)


def get_percent_std(a, b):
    """获取百分比字符串"""
    try:
        r = float(a) / b
    except ZeroDivisionError:
        return 0 if a == 0 else 100
    else:
        return "%.2f" % (r * 100)


def get_index(l):
    """获取已排序列表中元素变化时的下标，用于获取列表中相同元素的下标范围信息"""
    if len(l) <= 1:
        return
    indexs = [0]
    x = l[0]
    for index, item in enumerate(l):
        if x != item:
            x = item
            indexs.append(index)
    indexs.append(len(l))
    return indexs


def get_same_element(l):
    """获取列表中相同元素的下标"""
    indexs = []
    for i in range(len(l)):
        x = [i]
        for j in range((i+1), len(l)):
            if l[j] and l[j] == l[i]:
                x.append(j)
                l[j] = ''
        if len(x) > 1:
            indexs.append(x)
    return indexs


def sort_query(query, s_snid):
    """以日期和指定平台顺序对queryset数据进行排序"""
    if not s_snid:
        return query

    def f(k):
        w_snid = len(s_snid)
        if k.snid in s_snid:
            w_snid = s_snid.index(k.snid)
        return (k.ds, w_snid)
    return sorted(query, key=f)


def cache_filter(queryset, **option):
    """queryset 缓存filter"""
    return [query for query in queryset if all(getattr(query, k) == v for k, v in option.iteritems())]


def cache_get(queryset, **option):
    """queryset 缓存get"""
    result = cache_filter(queryset, **option)
    if len(result) != 1:
        raise ValueError("get should return one record, but now:%s" % len(result))
    return result[0]


def cache_in(queryset, in_kv):
    """
    in_kv = {"gameid":[]}
    """
    return [query for query in queryset if all(getattr(query, k) in v for k, v in in_kv.iteritems())]


def fast_cache_filter(queryset, *keys):
    """使用字典加速cache filter"""
    cache = defaultdict(list)

    for query in queryset:
        v = [getattr(query, key) for key in keys]
        cache[tuple(v)].append(query)

    def query_filter(**option):
        assert len(keys)==len(option), "filter keys and option must same"
        return cache.get([option[key] for key in keys], [])

    return query_filter


def fast_cache_get(queryset, *keys):
    """使用字典加速cache get"""
    query_filter = fast_cache_filter(queryset, *keys)

    def query_get(**option):
        result = query_filter(**option)
        if len(result) != 1:
            raise ValueError("get should return one record, but now:%s" % len(result))
        return result[0]

    return query_get


def get_yesterday():
    """昨天前日期"""
    return (datetime.datetime.now() + datetime.timedelta(days=-1)).date()


def get_ten_days_ago():
    """十天前日期"""
    return (datetime.datetime.now() + datetime.timedelta(days=-10)).date()


def get_current_month_one_day():
    """获取当月1号日期"""
    return datetime.date.today().replace(day=1)


def get_last_month_one_day():
    """获取上个月1号日期"""
    return (datetime.date.today().replace(day=1) - datetime.timedelta(1)).replace(day=1)


def get_last_month_last_day():
    """获取上个月最后一天的日期"""
    return datetime.date.today().replace(day=1) + datetime.timedelta(days=-1)


def last_month(date):
    """返回上个月的日期"""
    return date - relativedelta(months=1)


def amount(value):
    """金额表示
    不需要小数位，整数表示
    """
    return int(value)


def tp(value):
    """数字带有千位表示
    >>10000.10
    '10,000.1'
    """
    return "{:,}".format(value)


def arppu(value, cnt):
    """计算arppu
    取整
    """
    if cnt == 0:
        return 0
    try:
        return int(value / cnt)
    except ZeroDivisionError:
        return 0


def div(f, s, digit=None):
    try:
        r = float(f) / s
        if digit is not None:
            return "%.{0}f".format(digit) % r
        return r
    except ZeroDivisionError:
        return 0


def online_hour(f, s, digit=None):
    try:
        r=float(f) / s / 3600
        if digit is not None:
            return "%.{0}f".format(digit) % r
        return r
    except ZeroDivisionError:
        return 0


def groupby(iterable, byfunc, keyfunc, reverse=False):
    """获取一组值的最大值或最小值,　默认最大值
    iterable不要求有序(itertools.groupby要求有序)
    byfunc: 分组函数
    keyfunc: 最大值字段函数
    """
    exists = {}
    indexs = {}
    result = []
    for obj in iterable:
        by, value = byfunc(obj), keyfunc(obj)
        if by not in exists:
            exists[by] = value
            indexs[by] = len(result)
            result.append(obj)
        else:
            change = value > exists[by] if reverse else value < exists[by]
            if change:
                exists[by] = value
                result[indexs[by]] = obj

    return result


def run(cmd):
    """运行命令返回标准输出和标准错误输出"""
    msg = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True).stdout.read()
    return msg


def fab_call(name, *args):
    """fabric调用"""
    if args:
        other = " ".join(args)
    else:
        other = ""
    script = os.path.join(settings.BASE_DIR, "script", "fabfile")
    cmd = "fab -f {script} {name}:{other}".format(**locals())
    print(cmd)
    return run(cmd)


def db_query(db, query, *parameters, **kwparameters):
    """Returns a row list for the given query and parameters."""
    cursor = db._cursor()
    try:
        db._execute(cursor, query, parameters, kwparameters)
        column_names = [d[0] for d in cursor.description]
        return [torndb.Row(itertools.izip(column_names, row)) for row in cursor], column_names
    finally:
        cursor.close()


def sql_clause(keys):
    """sql语句拼接
    {"openid":111, "roleid":222}
    openid=111 and roleid=222
    """
    return "and".join([" %s='%s' " %(k, MySQLdb.escape_string(v)) for k, v in keys.iteritems() if v])


def check_int(value, sepcial="all"):
    if value != sepcial:
        _ = int(value)
    return value


def test():
    return {
        '00:00': {'yesterday_user': 100, 'today_user': 200},
        '00:05': {'yesterday_user': 200}
    }


def utf8_encode(stream):
    """检测文件/字符串编码，最终将其转为UTF8编码"""
    result = chardet.detect(stream)
    encoding = result['encoding']
    if encoding != 'utf-8':
        try:
            stream = stream.decode(encoding).encode('utf-8')
        except Exception:
            raise Exception(u'请使用utf8编码')
    return stream


if __name__ == "__main__":
    print test()
