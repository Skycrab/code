# coding=utf8

import os
import json
import datetime
from collections import defaultdict

import pandas as pd

from .. import util
from .. import ddl
from ..log import log


class Unit(object):
    """处理单元有优先级，优先级[-10, 10]高的先运行，默认0"""
    PR = 0

    # 统计维度
    DAU_DIMENSION = 1       # 日活维度
    NEW_DIMENSION = 2       # 新用户
    NEWPAY_DIMENSION = 3    # 新付费
    MISSING_DIMENSION = 4   # 流失用户
    PAY_DIMENSION = 5       # 付费用户
    HISPAY_DIMENSION = 7    # 历史付费用户
    FIRST_BIND_DIMENSION = 8        # 首次消耗蓝钻维度
    FIRST_UNBIND_DIMENSION = 9      # 首次消耗金钻维度
    DAU_NOPAY_DIMENSION = 10        # 活跃用户中免费用户

    def __init__(self, owner):
        self.owner = owner
        self.total_group = []

    def __getattr__(self, name):
        return getattr(self.owner, name)

    def set_up(self):
        """设置环境，可当__init__使用"""

    def tear_down(self):
        """所有gameid处理后调用"""

    def set_up_gameid(self, gameid):
        """单个gameid"""

    def tear_down_gameid(self, gameid):
        """单个gameid处理后调用"""

    def process(self):
        """默认处理方法，子类需定义process_dataframe()具体方法
        如默认process不满足，可自定义process()方法
        """
        table = self.Model.TABLE_NAME
        if table not in self.tables:
            return

        self.set_up()

        for gameid, merge in self.tables[table].iteritems():
            log.info("process gameid: %s, table: %s begin", gameid, table)
            df = util.read_csv(merge, names=self.Model.FIELDS, dtype=self.Model.Dtype)
            df2 = self.filter(gameid, df, self.Model)
            if df2.empty or not self.sure_analysis:
                log.info("process gameid(skip): %s, table: %s end", gameid, table)
                continue
            self.process_dataframe(gameid, df2)
            log.info("process gameid: %s, table: %s end", gameid, table)

        # 全game统计(由于有权限系统，由应用层汇总)
        # if self.total_group:
        #     total_df = pd.DataFrame(self.total_group)
        #     self.process_total(total_df)
        self.tear_down()

    def process_total(self, df):
        """所有gameid统计, gameid->snid(0->0, 0->1)"""

    def load_csv(self, model, gameid):
        """加载model对应的csv"""
        try:
            merge = self.tables[model.TABLE_NAME][gameid]
            return util.read_csv(merge, names=model.FIELDS, dtype=model.Dtype)
        except KeyError as e:
            log.error("load_csv error, gameid: %s, table: %s, error: %s", gameid, model.TABLE_NAME, e)
            return None


################

    def history_path(self, gameid, history_csv=None):
        """返回需要的历史csv文件"""
        if history_csv is None:
            history_csv = self.HISTORY_CSV
        return os.path.join(self.history, gameid, history_csv)

    def load_history(self, gameid, field=None, history_csv=None):
        """加载历史数据"""
        directory = os.path.join(self.history, gameid)
        if not os.path.exists(directory):
            os.makedirs(directory)
        path = self.history_path(gameid, history_csv)
        if not os.path.exists(path):
            util.create_file(path)
        if field is None:
            field = self.HISTORY_FIELDS
        return util.read_csv(path, names=field, dtype=ddl.Model.Dtype)

    def write_history_csv(self, data_frame, gameid):
        """历史csv写入"""
        data_frame.to_csv(self.history_path(gameid), header=False, index=False, mode='w', encoding="utf8")

###############

    def tmp_path(self, gameid, tmp_csv):
        """临时目录"""
        directory = os.path.join(self.tmp, gameid)
        if not os.path.exists(directory):
            os.makedirs(directory)
        return os.path.join(directory, tmp_csv)

    def load_tmp(self, gameid, tmp_csv):
        """加载临时数据
        临时表是带有header的
        """
        path = self.tmp_path(gameid, tmp_csv)
        if not os.path.exists(path):
            return None
        return util.read_csv(path, dtype=ddl.Model.Dtype)

    def write_tmp_csv(self, data_frame, gameid, tmp_csv):
        """临时csv写入"""
        data_frame.to_csv(self.tmp_path(gameid, tmp_csv), header=True, index=False, mode='w', encoding="utf8")

    def load_tmp_mysql(self, gameid, model, tmp_csv):
        """零时csv写入mysql"""
        path = self.tmp_path(gameid, tmp_csv)
        path = path.replace("\\", "\\\\")
        cmd = ddl.DDL.mysql_load_data(model, path, gameid, ignore=1)
        try:
            # print(cmd)
            os.system(cmd)
        except Exception as e:
            log.error("load_tmp_mysql error, path: %s, error: %s", path, e)

##############
    def load_date_delta(self, gameid, delta):
        """加载前几日Model对应的csv"""
        date = util.date_delta(self.today, delta)[0]
        directory = os.path.join(os.path.dirname(self.directory), date)
        if hasattr(self, "RelatedModel"):
            models = self.RelatedModel
        else:
            models = [self.Model]
        dfs = []
        for model in models:
            csv = "{0}_merge.csv".format(gameid)
            path = os.path.join(directory, model.TABLE_NAME, csv)
            if os.path.exists(path):
                dfs.append(util.read_csv(path, names=model.FIELDS, dtype=model.Dtype))
            else:
                dfs.append(pd.DataFrame([], columns=model.FIELDS))
        if len(dfs) == 1:
            return dfs[0]
        return dfs

    def load_all_role(self, gameid, index=["openid", "clientid"]):
        """加载今日all_role文件
        """
        name = "{0}.csv".format(self.date)
        path = os.path.join(self.role_directory, gameid, name)
        df = pd.read_csv(path, names=ddl.AllRole.FIELDS, dtype=ddl.AllRole.Dtype)
        df.drop_duplicates(subset=index, inplace=True)
        return df.set_index(index)

    def load_all_role_multi_roleid(self, gameid, index=["openid", "clientid", "roleid"]):
        """加载今日all_role文件
        """
        name = "{0}.csv".format(self.date)
        path = os.path.join(self.role_multi_roleid_directory, gameid, name)
        df = pd.read_csv(path, names=ddl.AllRoleMultiRoleid.FIELDS, dtype=ddl.AllRoleMultiRoleid.Dtype)
        df.drop_duplicates(subset=index, inplace=True)
        return df.set_index(index)

    def save_all_role(self, gameid, df):
        name = "{0}.csv".format(self.date)
        path = os.path.join(self.role_directory, gameid, name)
        df = df.reset_index()
        df.to_csv(path, header=False, index=False, columns=ddl.AllRole.FIELDS, mode='w', encoding="utf8")

    def save_all_role_multi_roleid(self, gameid, df):
        name = "{0}.csv".format(self.date)
        path = os.path.join(self.role_multi_roleid_directory, gameid, name)
        df = df.reset_index()
        df.to_csv(path, header=False, index=False, columns=ddl.AllRoleMultiRoleid.FIELDS, mode='w', encoding="utf8")

#############
    def filter(self, gameid, df, model, clientid=None):
        """过滤df,主要是处理补数据情况
        比如在1号数据中发现7号数据，或相反
        """
        if df.empty:
            return df
        try:
            timestamp_column = model.TIMESTAMP or filter(lambda x: x.endswith("_time"), model.FIELDS)[0]
        except Exception as e:
            log.error("table:%s has no timestamp filed", model.TABLE_NAME)
            return df
        series = df[timestamp_column]
        t_max, t_min = series.max(), series.min()
        if self.start <= t_min and self.end >= t_max:
            return df

        if not self.enable_filter:
            # 如果是多次运行(cron, 不要分发)
            boolean = (df[timestamp_column]>=self.start) & (df[timestamp_column]<self.end)
            return df[boolean]

        # ValueError: timestamp out of range for platform localtime()/gmtime() functio
        try:
            d_max, d_min = datetime.datetime.fromtimestamp(t_max), datetime.datetime.fromtimestamp(t_min)
        except ValueError as e:
            log.error("gameid:%s, table:%s fromtimestamp error,%s", gameid, model.TABLE_NAME, str(e))
            boolean = (df[timestamp_column]>=self.start) & (df[timestamp_column]<self.end)
            return df[boolean]

        msg = json.dumps({"d_max": str(d_max), "d_min": str(d_min), "gameid": gameid, "table": model.TABLE_NAME})
        group = {"gameid": gameid, "ds": self.date, "type": ddl.Log.FILTER_TYPE, "msg": msg}
        ddl.Log.insert(group)
        _error = """
        ######date error######
        gameid:{0}, table: {1}, handle date:{2}
        csv min date:{3}, max date:{4}
        please check whether restart the task"""
        log.warning(_error.format(gameid, model.TABLE_NAME, self.date, str(d_min), str(d_max)))
        # 分发相应数据到对应天的csv中
        delta = d_max.date() - d_min.date()
        for d in range(delta.days + 1):
            date = d_min.date() + datetime.timedelta(d)
            if date == self.today:
                continue
            start = util.date_delta(date, delta=0)[1]
            end = util.date_delta(date, delta=1)[1]
            boolean = (df[timestamp_column]>=start) & (df[timestamp_column]<end)
            df_tmp = df[boolean]
            if df_tmp.empty:
                continue
            path = os.path.join(os.path.dirname(self.directory), str(date), model.TABLE_NAME)
            if clientid is not None:
                path = os.path.join(path, clientid)
            if not os.path.exists(path):
                log.warning("data error, path:%s not exists", path)
                os.makedirs(path)
            csv = "{0}_append_{1}.csv".format(gameid, str(self.today))
            name = os.path.join(path, csv)
            # 不分发昨天的数据(见analysis cut)
            if (self.today - date).days == 1:
                continue
            df_tmp.to_csv(name, header=False, columns=model.FIELDS, index=False, mode='w', encoding="utf8")

        boolean = (df[timestamp_column]>=self.start) & (df[timestamp_column]<self.end)
        return df[boolean]


##############
    def dimension_group(self, gameid, dimension):
        return {
            "dimension": dimension,
            "clientid": defaultdict(dict),
            "all": defaultdict(dict),
            "gameid": gameid
        }


class RelatedUnit(Unit):
    """关联单元, 计算时需要多个csv
    如果关联太强，可在owner中使用共享变量
    如果关联数据量过大，建议状态使用零时csv保持
    """

    def process(self):
        """"关联单元需定义关联的RelatedModel
        """
        games = [self.tables.get(model.TABLE_NAME, {}) for model in self.RelatedModel]

        # 获取所有gameid
        gameids = set()
        for game in games:
            gameids.update(game)

        self.set_up()

        for gameid in gameids:
            dfs = []
            for ix, game in enumerate(games):
                if gameid in game:
                    df = util.read_csv(game[gameid], names=self.RelatedModel[ix].FIELDS, dtype=self.RelatedModel[ix].Dtype)
                    df2 = self.filter(gameid, df, self.RelatedModel[ix])
                    dfs.append(df2)
                else:
                    dfs.append(pd.DataFrame([], columns=self.RelatedModel[ix].FIELDS))
            if self.sure_analysis:
                self.process_dataframe(gameid, *dfs)

        # if self.total_group:
        #     total_df = pd.DataFrame(self.total_group)
        #     self.process_total(total_df)

        self.tear_down()


class ClientSplitUnit(Unit):

    def process(self):
        """默认处理方法，子类需定义process_dataframe()具体方法
        如默认process不满足，可自定义process()方法
        """
        table = self.Model.TABLE_NAME
        if table not in self.tables:
            return

        self.set_up()

        for gameid, fs in self.tables[table].iteritems():
            self.set_up_gameid(gameid)
            for clientid, merge in fs.iteritems():
                log.info("process gameid: %s, table: %s, clientid: %s begin", gameid, table, clientid)
                df = util.read_csv(merge, names=self.Model.FIELDS, dtype=self.Model.Dtype)
                df2 = self.filter(gameid, df, self.Model, clientid=clientid)
                if df2.empty or not self.sure_analysis:
                    log.info("process gameid: %s, table: %s, clientid: %s end", gameid, table, clientid)
                    continue
                self.process_dataframe(gameid, clientid, df2)
                log.info("process gameid: %s, table: %s, clientid: %s end", gameid, table, clientid)

            self.tear_down_gameid(gameid)
        self.tear_down()


class NoModelUnit(Unit):

    def process(self):
        self.set_up()
        for gameid in self.gameids:
            self.process_dataframe(gameid)
        self.tear_down()
