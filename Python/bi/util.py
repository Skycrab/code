# coding=utf8

import os
import time
import datetime
import calendar
from dateutil.relativedelta import relativedelta

import pandas as pd


class class_property(object):
    """ A property can decorator class or instance

    class Foo(object):
        @class_property
        def foo(cls):
            return 42

    print(Foo.foo)
    print(Foo().foo)

    """
    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ == doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        value = self.func(type)
        return value


class class_cached_property(object):

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if cls is None:
            return self
        value = self.func(cls)
        setattr(cls, self.func.__name__, value)
        return value


class cached_property(object):
    """ A property that is only computed once per instance and then replaces
        itself with an ordinary attribute. Deleting the attribute resets the
        property. """

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


def get_gameid_from_history(history):
    """从history目录获取所有gameid信息"""
    return {gameid for gameid in os.listdir(history) if gameid.isdigit()}


def read_csv(csv, names=None, dtype=None):
    df = pd.read_csv(csv, names=names, dtype=dtype)
    return df


def timestamp(date):
    """convert date or datetime to timestamp"""
    return int(time.mktime(date.timetuple()))


def datetime_timestamp(d, t):
    array = time.strptime("{0} {1}".format(d, t), "%Y-%m-%d %H:%M:%S")
    return int(time.mktime(array))


def is_valid_date(str):
    '''判断是否是一个有效的日期字符串'''
    try:
        time.strptime(str, "%Y-%m-%d")
        return True
    except:
        return False


def todate(date):
    """date string to datetime.date"""
    return datetime.datetime.strptime(date, "%Y-%m-%d").date()


def month_date(month):
    """convert 2015-08 to date"""
    return datetime.datetime.strptime(month, "%Y-%m").date()


def date_string(date):
    """datetime.date to string"""
    return date.strftime("%Y-%m-%d")


def date_delta(date, delta=1):
    """"日期间隔"""
    if delta >= 0:
        new = date + datetime.timedelta(delta)
    else:
        new = date - datetime.timedelta(-delta)

    return new.strftime("%Y-%m-%d"), int(time.mktime(new.timetuple()))


def next_month(date):
    """返回下个月的日期"""
    return date + datetime.timedelta(calendar.monthrange(date.year, date.month)[1])


def last_month(date):
    """返回上个月的第一天"""
    return date - relativedelta(months=1)


def lastday_month(date):
    """返回上个月的最后一天"""
    return datetime.date(date.year, date.month, 1) - datetime.timedelta(1)


def endday_month(date):
    """返回当月最后一天"""
    return (date + datetime.timedelta(calendar.monthrange(date.year, date.month)[1])) - datetime.timedelta(1)


def create_file(path):
    """创建文件"""
    with open(path, 'w'):
        pass


def copy(src, dst):
    while 1:
        block = src.read(20480)
        if not block:
            break
        dst.write(block)


def merge(merge, parts):
    """合并文件"""
    with open(merge, "w") as dst:
        for part in parts:
            with open(part) as src:
                copy(src, dst)
                # os.remove(src)


def percent(count, total):
    """返回百分比万表示"""
    percent = float(count) / total
    return int(percent * 10000)


def remove_multi(columns, *args):
    """list移除多个值"""
    tmp = list(columns)
    for v in args:
        tmp.remove(v)
    return tmp


def test():
    class Foo(object):
        @class_cached_property
        def foo(cls):
            print("foo")
            return 42

    print(Foo.foo)


def test2():
    print(datetime_timestamp('2015-08-12', '04:03:08'))


if __name__ == "__main__":
    test2()
