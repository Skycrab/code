# coding=utf8

import os
import re
import datetime

import pandas as pd

import util
import config
from ddl import DDL
from log import log
from realtime import MinuteInterval
from manage import Manage
from unit import LoadAllUser


class Style(object):
    Header = re.compile(r"BI_(?P<table>[\w_]+)\|(?P<other>(.+))")

    def __init__(self, directory, hour, history):
        self.directory = directory
        self.hour = hour
        self.history = history
        self.tmp = os.path.join(self.directory, "tmp")
        self.today = util.todate(os.path.split(self.directory)[-1])
        self.gameid = set()
        self.data = {}
        self.data_frame = {}
        self.csv = []
        self.csv_unique = set()

    def set_up(self):
        for table in self.tables:
            self.data[table] = []
        # 加载汇率
        self.val_rates = Manage.val_rate
        self.rmb_rates = Manage.rmb_rate
        self.openids = Manage.filter_openid(self.history)
        # 新用户入库
        self.alluser = LoadAllUser(self)

    def filter_row(self, table, group):
        """过滤修改行，丢弃返回False"""
        return True

    def get_kvgroup(self, line, table, row):
        """返回kv字典"""

    def filter_payment(self, group):
        """支付汇率计算
        可能出现amount为空，此时根据val计算
        """
        try:
            amount = float(group.get("amount", 0) or 0)
            val = float(group.get("val", 0) or 0)
            if amount != 0:
                group["amount"] = amount * self.rmb_rates[group["currency"].lower()]
            else:
                group["amount"] = val * self.val_rates[group["gameid"]]
            if val == 0:
                group["val"] = amount / self.val_rates[group["gameid"]]
            group["currency"] = "rmb"
        except Exception as e:
            log.error("filter_payment error, %s, group:\n%s", str(e), group)
            return False

        return True

    def filter_openid(self, group):
        """过滤账号ID"""
        if not self.openids:
            return True
        if group.get("gameid") not in self.openids:
            return True
        if group.get("openid") in self.openids[group.get("gameid")]:
            return False

        return True

    def process(self, table, group):
        """处理每条的kv字典, 默认值处理"""
        self.gameid.add(group["gameid"])

        fields = self.tables[table].FIELDS
        defaults = self.tables[table].DEFAULTS
        # 如果有多个_time字段，model会定义TIMESTAMP属性
        timestamp = self.tables[table].TIMESTAMP
        row = []
        for f in fields:
            v = group.get(f, "")
            if v != "":
                row.append(v)
                continue
            if f in defaults:
                v = defaults.get(f, "")
            elif f.endswith("_time") and (timestamp == "" or f == timestamp):
                if "timestamp" in group and group["timestamp"] != "0":   # 新版取timestamp
                    v = group["timestamp"]
                else:
                    v = util.datetime_timestamp(group["ds"], group["time"])
            row.append(v)

        self.data[table].append(row)

    def tear_down(self):
        """如果有需要特殊处理的表，会调用process_{table}"""
        for table in self.tables:
            self.data_frame[table] = pd.DataFrame(data=self.data[table], columns=self.tables[table].FIELDS)

        ignore = []
        for table in self.tables:
            func = "process_{0}".format(table)
            if hasattr(self, func):
                ignore.append(table)
                getattr(self, func)(table)

        # save csv
        for table in self.tables:
            if table in ignore:
                continue
            else:
                df = self.data_frame[table]
                self.save(df, table)

        # store mysql
        self.storage()
        if not config.disable_realtime:  # 没有禁用实时分析
            self.real_time_analysis()

    def save(self, df, table):
        """DataFrame保存csv文件"""
        if df.empty:
            return
        model = self.tables[table]
        store, fields, client_split = model.TABLE_NAME, model.FIELDS, model.CLIENT_SPLIT

        def to_csv(path, df_store):
            if not os.path.exists(path):
                os.makedirs(path)
            name = os.path.join(path, "{0}_{1}.csv".format(gameid, self.hour))
            if name not in self.csv_unique:
                self.csv_unique.add(name)
                self.csv.append((name, gameid, store))

            # 这里mode是a,存在多个table对应一个store(role_login_in,role_login_out对应RoleLogin)
            try:
                df_store.to_csv(name, header=False, columns=fields, index=False, mode='a', encoding="utf8")
            except Exception as e:
                log.error("extract save to csv name: %s, error, %s", name, e)

        for gameid in self.gameid:
            df2 = df[df.gameid == gameid]
            if df2.empty:
                continue
            if client_split:  # 按区服分割
                clientids = df2.clientid.unique()
                for clientid in clientids:
                    df_client = df2[df2.clientid == clientid]
                    path = os.path.join(self.directory, store, clientid)
                    to_csv(path, df_client)
            else:
                path = os.path.join(self.directory, store)
                to_csv(path, df2)

            # 入库all_user(减少实时数据新用户计算)
            if table == "login" and not config.disable_realtime:
                try:
                    self.alluser.process_dataframe(gameid, df2)
                except Exception as e:
                    log.error("extract alluser process error, %s, gameid, %s", e, gameid)

    def storage(self):
        """csv入库mysql"""
        for path, gameid, table in self.csv:
            # DDL.create(table, gameid)
            path = path.replace("\\", "\\\\")
            try:
                model = DDL.TABLES[table]
                # print(table, model.STORE)
                if model.STORE:
                    cmd = DDL.mysql_load_data(table, path, gameid)
                    os.system(cmd)
            except Exception as e:
                log.error("extract mysql loaddata error, %s, path: %s", e, path)

    @property
    def online_df(self):
        """获取实时在线dataframe"""
        return self.data_frame.get("online")

    def real_time_analysis(self):
        """实时数据分析"""
        realtime = MinuteInterval(self)
        s = "{0} {1}".format(self.today, self.hour)
        now = datetime.datetime.strptime(s, "%Y-%m-%d %H%M")
        realtime.process(now)


class OldStyle(Style):
    Login = re.compile(r".*?\|openid{(?P<openid>.+?)}\|source{(?P<device>.*?)}.*?\|creative{(?P<OS>.*?)}\|family{(?P<MAC>.*?)}.*?\|ip{(?P<IP>.*?)}.*?\|login_date{(?P<ds>.+?)}\|login_time{(?P<time>[^}]+?)}.*?\|snid{(?P<snid>[^}]+?)}.*?\|gameid{(?P<gameid>.+?)}")
    Install = re.compile(r".*?\|openid{(?P<openid>[^}]+?)}.*?\|ip{(?P<IP>.*?)}\|install_date{(?P<ds>.+?)}\|install_time{(?P<time>[^}]+?)}.*?\|snid{(?P<snid>.+?)}\|clientid{(?P<clientid>.+?)}\|gameid{(?P<gameid>.+?)}")
    Role_Login = re.compile(r"roleid{(?P<roleid>[^}]+?)}.*?\|openid{(?P<openid>.+?)}\|ip{(?P<IP>.*?)}\|level{(?P<level>[^}]+?)}.*?\|rolelogin_date{(?P<ds>.+?)}\|rolelogin_time{(?P<time>[^}]+?)}.*?\|snid{(?P<snid>.+?)}\|clientid{(?P<clientid>.+?)}\|gameid{(?P<gameid>.+?)}")
    Role_Logout = re.compile(r"roleid{(?P<roleid>[^}]+?)}.*?\|openid{(?P<openid>.+?)}\|ip{(?P<IP>.*?)}\|level{(?P<level>[^}]+?)}.*?\|online_time{(?P<online_time>.*?)}.*?\|rolelogout_date{(?P<ds>.+?)}\|rolelogout_time{(?P<time>[^}]+?)}.*?\|snid{(?P<snid>.+?)}\|clientid{(?P<clientid>.+?)}\|gameid{(?P<gameid>.+?)}")
    Levelup = re.compile(r"roleid{(?P<roleid>[^}]+?)}.*?\|openid{(?P<openid>.+?)}\|levelup{(?P<levelup>.+?)}\|kingdom{(?P<kingdom>[^}]*?)}.*?\|val{(?P<level>[^}]+?)}.*?\|ip{(?P<IP>.*?)}\|levelup_date{(?P<ds>.+?)}\|levelup_time{(?P<time>[^}]+?)}.*?\|snid{(?P<snid>.+?)}\|clientid{(?P<clientid>.+?)}\|gameid{(?P<gameid>.+?)}")
    Online = re.compile(r".*?\|users{(?P<users>.+?)}\|online_date{(?P<ds>.+?)}\|online_time{(?P<time>[^}]+?)}.*?\|snid{(?P<snid>.+?)}\|clientid{(?P<clientid>.+?)}\|gameid{(?P<gameid>.+?)}")
    Payment = re.compile(r".*?\|openid{(?P<openid>.+?)}\|amount{(?P<amount>.*?)}\|currency{(?P<currency>[^}]*?)}.*?\|transactionid{(?P<transactionid>.*?)}.*?\|val{(?P<val>.*?)}.*?\|payment_date{(?P<ds>.+?)}\|payment_time{(?P<time>[^}]+?)}.*?\|snid{(?P<snid>.+?)}\|clientid{(?P<clientid>.+?)}\|gameid{(?P<gameid>.+?)}")
    Consume = re.compile(r"roleid{(?P<roleid>[^}]+?)}.*?\|openid{(?P<openid>[^}]+?)}.*?\|amount{(?P<consume_sum>[^}]+?)}.*?\|own_after{(?P<own_after>.*?)}\|level{(?P<level>.+?)}\|kingdom{(?P<kingdom>[^}]+?)}.*?\|genus{(?P<goodsid>.*?)}\|val{(?P<goodsnum>.*?)}\|ip{(?P<IP>.*?)}\|consume_date{(?P<ds>.+?)}\|consume_time{(?P<time>[^}]+?)}.*?\|snid{(?P<snid>.+?)}\|clientid{(?P<clientid>.+?)}\|gameid{(?P<gameid>.+?)}")
    Mission = re.compile(r'roleid{(?P<roleid>[^}]+?)}.*?\|openid{(?P<openid>.+?)}\|level{(?P<level>.+?)}\|mission{(?P<mission_level>.+?)}\|kingdom{(?P<event_ID>[^}]+?)}.*?\|status{(?P<event_OK>.+?)}\|ip{(?P<IP>.*?)}\|mission_date{(?P<ds>.+?)}\|mission_time{(?P<time>[^}]+?)}.*?\|snid{(?P<snid>.+?)}\|clientid{(?P<clientid>.+?)}\|gameid{(?P<gameid>.+?)}')
    Role_Unique = ["openid", "gameid", "clientid", "snid", "roleid"]
    Zhuanqu = re.compile(r"gameid{(?P<gameid>.+?)}\|openid{(?P<openid>.+?)}\|src{(?P<src>.+?)}.*?\|dst{(?P<dst>.+?)}")

    def __init__(self, directory, hour, history):
        self.tables = DDL.OLD_TABLES
        super(OldStyle, self).__init__(directory, hour, history)

    def process_install(self, table):
        """特殊处理install, table为install
           install表需要结合role_login表，获取roidid
        """
        new_role = self.data_frame[table]
        role_login = self.data_frame["role_login"][OldStyle.Role_Unique]
        role_login = role_login.drop_duplicates(subset=OldStyle.Role_Unique)
        new_role.drop("roleid", axis=1, inplace=True)
        new_role = new_role.merge(role_login, on=OldStyle.Role_Unique[:-1], how="left")
        new_role.fillna("")
        self.save(new_role, table)

    def filter_row(self, table, group):
        """过滤处理每一行的kv字典
           丢弃返回False
        """
        if table != "online":
            if group.get("snid") == "0" or group.get("clientid") == "0":
                return False

        if table == "consume":
            if group.get("kingdom") != "consume":
                return False
            return self.filter_openid(group)
        elif table == "mission":
            mission, status = group["mission_level"], group["event_OK"]
            if status in ["start"]:
                return False
            # 以新版为准,2为通过,过度版２为失败
            group["event_OK"] = 1 if status in ("failed", "2") else 2
            if mission in ["battle", "battle-h"]:
                group["mission_type"] = 1       # 关卡
            else:
                group["mission_type"] = 2       # 任务
        elif table == "payment":
            if not self.filter_openid(group):
                return False
            if group["currency"] != "rmb":    # 汇率计算
                return self.filter_payment(group)
        elif table == "levelup" and group["levelup"] not in ("1", "bridge_up", "team_up"):
            return False
        elif table == "zhuanqu":
            group["ds"] = str(self.today)

        return True

    def get_kvgroup(self, line, table, row):
        """返回kv字典"""
        name = table.title()
        pattern = getattr(self, name) if hasattr(self, name) else None
        if pattern is None:
            # log.error("header:%s not recognize , please check, line:%d, data:\n%s", table, line, row)
            return
        match = pattern.search(row)
        if not match:
            log.error("row field error, please check, line:%d, table:%s, data:\n%s", line, table, row)
            return
        group = match.groupdict()
        return group


class NewStyle(Style):
    Login = set(["gameid", "snid", "openid", "login_timestamp"])
    Role_New = set(["gameid", "clientid", "snid", "openid", "roleid", "role_timestamp"])
    Role_Login = set(["gameid", "clientid", "snid", "type", "openid", "rolelogin_timestamp"])
    Levelup = set(["gameid", "clientid", "snid", "openid", "level", "levelup_timestamp"])
    Payment = set(["gameid", "clientid", "snid", "openid", "currency", "payment_timestamp"])
    Consume = set(["gameid", "clientid", "snid", "openid", "consume_sum", "consume_timestamp"])
    Mission = set(["gameid", "clientid", "snid", "openid", "mission_type", "event_ID", "event_OK", "mission_timestamp"])
    Online = set(["gameid", "clientid", "users", "online_timestamp"])
    Props_Get = set(["gameid", "clientid", "snid", "openid", "propsid", "get_timestamp"])
    Props_Consume = set(["gameid", "clientid", "snid", "openid", "propsid", "consume_timestamp"])
    Gold_Get = set(["gameid", "clientid", "snid", "openid", "get_timestamp"])
    Gold_Consume = set(["gameid", "clientid", "snid", "openid", "consume_timestamp"])
    Blue_Diamond_Get = set(["gameid", "clientid", "snid", "openid", "get_timestamp"])
    Yellow_Diamond_Get = set(["gameid", "clientid", "snid", "openid", "get_timestamp"])
    Consume_D = set(["gameid", "clientid", "snid", "openid", "consume_timestamp"])
    Other_Get = set(["gameid", "clientid", "snid", "openid", "get_timestamp", "currency_type"])
    Other_Consume = set(["gameid", "clientid", "snid", "openid", "consume_timestamp", "currency_type"])

    def __init__(self, directory, hour, history):
        self.tables = DDL.NEW_TABLES
        super(NewStyle, self).__init__(directory, hour, history)

    def filter_row(self, table, group):
        """过滤处理每一行的kv字典
           丢弃返回False
        """
        if table != "online":
            if group.get("snid") == "0" or group.get("clientid") == "0":
                return False
        if table == "consume":
            return self.filter_openid(group)
        elif table == "payment":
            if not self.filter_openid(group):
                return False
            if group["currency"] != "CNY":    # 汇率计算
                return self.filter_payment(group)

        return True

    def get_kvgroup(self, line, table, row):
        """返回kv字典"""
        name = table.title()
        check_field = getattr(self, name) if hasattr(self, name) else None
        if check_field is None:
            # log.error("header:%s not recognize , please check, line:%d, data:\n%s", table, line, row)
            return
        group = {}
        for field in row.split("|"):
            start, end = field.find('{'), field.rfind('}')
            k, v = field[:start], field[start + 1:end]
            if k in check_field and v == "":
                log.error("row field error, please check, line:%d, table:%s, data:\n%s", line, table, row)
                return
            # 有些表需要ds字段
            if k.endswith("_date"):
                k = "ds"
            elif k.endswith("_time"):
                if table == "online":
                    k = "time"
                elif k != "online_time":
                    k = "time"
            elif k.endswith("_timestamp"):
                k = "timestamp"
            group[k] = v

        return group


class Extract(object):
    def __init__(self, name, style="new", directory="csv", history="history"):
        self.name = name   # name like 'xx/xx/hour.log'
        hour = os.path.splitext(os.path.split(name)[-1])[0]
        # support 510038_2016-04-27-00-00-01-0001_6277895246370045952
        if hour.find('-') != -1:
            hour = ''.join(hour.split('-')[3:5])

        self.style = NewStyle(directory, hour, history) if style=="new" else OldStyle(directory, hour, history)

    def start(self):
        self.style.set_up()
        nu = 0
        with open(self.name) as f:
            for line in f:
                nu += 1
                row = line.strip()
                if row == "":
                    continue
                try:
                    self.process(row, nu)
                except Exception as e:
                    log.error("process row error:%s, data:%s", str(e), row)

        self.style.tear_down()

    def process(self, row, line):
        header = self.style.Header.search(row)
        if not header:
            log.error("row header error, please check,line:%d,data:\n%s", line, row)
            return
        table, other = header.group("table"), header.group("other")
        if not table or not other:
            return
        group = self.style.get_kvgroup(line, table, other)
        if group and self.style.filter_row(table, group):
            self.style.process(table, group)


def run(name, style, directory, history):
    extract = Extract(name, style, directory, history)
    extract.start()


def test():
    extract = Extract("log/1045.log", "old")
    extract.start()


if __name__ == "__main__":
    # t = Test()
    # t.test_logout()
    test()
