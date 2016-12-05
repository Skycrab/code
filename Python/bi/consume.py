# coding=utf8

import heapq
import operator
from collections import defaultdict

import pandas as pd
import numpy as np

from unit import Unit
from login import LoginUnit
from role import RoleUnit
from payment import PaymentUnit
from vip_consume import VipConsume
from .. import config
from role_resident import RoleResident
from ..log import log
from .. import ddl


class ConsumeUint(Unit):
    """消耗统计"""
    Model = ddl.Consume

    def process_dataframe(self, gameid, df):
        df.fillna(0, inplace=True)

        self.cal_dau_dimension(gameid, df)
        self.cal_newer_dimension(gameid, df)
        self.cal_newpay_dimension(gameid, df)
        self.cal_pay_dimension(gameid, df)
        self.cal_hispay_dimension(gameid, df)
        self.cal_total_gold(gameid, df)

        self.cal_pay_rich(gameid, df)
        self.update_all_role(gameid, df)

        if config.multi_roleid:
            self.cal_pay_rich_multi_roleid(gameid, df)
            self.update_all_role_multi_roleid(gameid, df)

        # 计算vip等级维度
        vipconsume = VipConsume(self, gameid, df)
        vipconsume.process()

    def cal_dau_dimension(self, gameid, df):
        """dau维度计算"""
        group = self.dimension_group(gameid, self.DAU_DIMENSION)

        self.cal_comsume_point(df, group)

        self.storage(group)

    def cal_newer_dimension(self, gameid, df):
        """新用户维度计算"""
        group = self.dimension_group(gameid, self.NEW_DIMENSION)
        # 获取该日新增用户
        df_append = self.load_tmp(gameid, LoginUnit.TMP_LOGIN_NEW_CSV)
        if df_append is None or df_append.empty:
            return
        df = df[df["openid"].isin(df_append["openid"])]

        self.cal_comsume_point(df, group)

        self.storage(group)

    def cal_newpay_dimension(self, gameid, df):
        """新付费维度计算"""
        df_pay = self.load_tmp(gameid, PaymentUnit.TMP_PAYMENT_NEW_CSV)
        if df_pay is None or df_pay.empty:
            return
        df = df[df["openid"].isin(df_pay["openid"])]

        group = self.dimension_group(gameid, self.NEWPAY_DIMENSION)

        self.cal_comsume_point(df, group)
        self.storage(group)

    def cal_pay_dimension(self, gameid, df):
        """所有付费用户维度计算"""
        df_pay_all = self.load_csv(ddl.PayMent, gameid)
        if df_pay_all is None or df_pay_all.empty:
            return
        df = df[df["openid"].isin(df_pay_all["openid"])]
        group = self.dimension_group(gameid, self.PAY_DIMENSION)
        self.cal_comsume_point(df, group)
        self.storage(group)

    def cal_hispay_dimension(self, gameid, df):
        """所有历史付费用户维度计算"""
        df_pay_his = self.load_tmp(gameid, RoleUnit.TMP_ROLE_HISPAY)
        if df_pay_his is None or df_pay_his.empty:
            return
        df = df[df["openid"].isin(df_pay_his["openid"])]
        group = self.dimension_group(gameid, self.HISPAY_DIMENSION)
        self.cal_comsume_point(df, group)
        self.storage(group)

    def cal_comsume_point(self, df, group):
        """消费点分析"""
        # 计算消费人数和消费人次,物品消耗总量
        df2 = df.groupby(["clientid", "goodsid"]).agg({"openid": {"total_cnt": len, "unique_cnt": lambda x: len(x.unique())}, "consume_sum": np.sum, "goodsnum": np.sum})
        for t in df2.itertuples():
            (clientid, goodsid), consume_cnt, consume_per, consume_goodsnum, consume_sum = t
            group["clientid"][clientid][goodsid] = {"consume_cnt": consume_cnt, "consume_per": consume_per, "consume_sum": consume_sum, "consume_goodsnum": consume_goodsnum}

        # 全服
        df3 = df.groupby("goodsid").agg({"openid": {"total_cnt": len, "unique_cnt": lambda x: len(x.unique())}, "consume_sum": np.sum, "goodsnum": np.sum})
        for t in df3.itertuples():
            goodsid, consume_cnt, consume_per, consume_goodsnum, consume_sum = t
            group["all"][goodsid] = {"consume_cnt": consume_cnt, "consume_per": consume_per, "consume_sum": consume_sum, "consume_goodsnum": consume_goodsnum}

        # #计算消费金额()
        #
        # for name,g in df.groupby(["clientid", "goodsid"]):
        #     clientid, goodsid = name
        #     consume_sum = 0
        #     for gg in g.values:
        #         consume_sum += gg[-2]*gg[-1]
        #     group["clientid"][clientid][goodsid]["consume_sum"] = consume_sum
        #     group["all"][goodsid].setdefault("consume_sum", 0)
        #     group["all"][goodsid]["consume_sum"] += consume_sum

    def cal_total_gold(self, gameid, df):
        """计算消耗金币数
        此时goodsid为0，cunsume_cnt为消耗金币数
        """
        gold_dimension = 6
        group = self.dimension_group(gameid, gold_dimension)
        df2 = df.groupby("clientid").consume_sum.sum()
        total = 0
        for clientid, cnt in df2.iteritems():
            total += cnt
            group["clientid"][clientid][0] = {"consume_cnt": cnt}
        group["all"][0] = {"consume_cnt": total}
        self.storage(group)

    def storage(self, group):
        common = {"gameid": group["gameid"], "ds": self.date, "dimension": group["dimension"]}
        group_list = []

        for clientid, values in group["clientid"].iteritems():
            tmp = dict(common)
            tmp["clientid"] = clientid
            for goodsid, v in values.iteritems():
                tmp2 = dict(tmp)
                tmp2["goodsid"] = goodsid
                tmp2.update(v)
                group_list.append(tmp2)

        for goodsid, v in group["all"].iteritems():
            tmp = dict(common)
            tmp["clientid"] = 0
            tmp["goodsid"] = goodsid
            tmp.update(v)
            group_list.append(tmp)

        # print(group_list)
        ddl.ConsumeDay.insert(group_list)

    def cal_pay_rich(self, gameid, df):
        """计算富豪榜的消耗数"""
        rich_df = self.load_tmp(gameid, PaymentUnit.TMP_PAYRICH_CSV)
        if rich_df is None or rich_df.empty:
            return
        df2 = df[df.openid.isin(rich_df.openid)]
        # consume_all = dict(df.groupby(["openid", "clientid"]).consume_sum.sum())
        # consume_all -> {(openid, clientid):sum}
        group = defaultdict(list)
        all_role = []
        consume_all = {}
        df3 = df2.groupby(["openid", "clientid"]).agg({"consume_sum": np.sum, "own_after": lambda x: x.iloc[-1]})
        for key, v in df3.iterrows():
            consume_all[key] = dict(v)

        for (_, openid, clientid, snid, amount, val) in rich_df.itertuples():
            tmp = {"openid": openid, "clientid": clientid, "amount": amount, "val": val}
            tmp.update(consume_all.get((openid, clientid), {}))
            all_role.append(tmp)
            group[snid].append(tmp)

        # 所有平台TOPN名
        group[0] = heapq.nlargest(PaymentUnit.TOPN, all_role, key=operator.itemgetter("amount"))

        # storage
        group_list = []
        for snid, topn in group.iteritems():
            for n, top in enumerate(topn, 1):
                tmp = {"gameid": gameid, "ds": self.date, "snid": snid, "rank": n}
                tmp.update(top)
                group_list.append(tmp)
        # print("****", group_list)
        ddl.PayRich.insert(group_list)

    def cal_pay_rich_multi_roleid(self, gameid, df):
        """计算富豪榜的消耗数"""
        rich_df = self.load_tmp(gameid, PaymentUnit.TMP_PAYRICH_MULTI_ROLEID_CSV)
        if rich_df is None or rich_df.empty:
            return
        df2 = df[df.openid.isin(rich_df.openid)]
        # consume_all = dict(df.groupby(["openid", "clientid"]).consume_sum.sum())
        # consume_all -> {(openid, clientid):sum}
        group = defaultdict(list)
        all_role = []
        consume_all = {}
        df3 = df2.groupby(["openid", "clientid", "roleid"]).agg({"consume_sum": np.sum, "own_after": lambda x: x.iloc[-1]})
        for key, v in df3.iterrows():
            consume_all[key] = dict(v)

        for (_, openid, clientid, roleid, snid, amount, val) in rich_df.itertuples():
            tmp = {"openid": openid, "clientid": clientid, "roleid": roleid, "amount": amount, "val": val}
            tmp.update(consume_all.get((openid, clientid, roleid), {}))
            all_role.append(tmp)
            group[snid].append(tmp)

        # 所有平台TOPN名
        group[0] = heapq.nlargest(PaymentUnit.TOPN, all_role, key=operator.itemgetter("amount"))

        # storage
        group_list = []
        for snid, topn in group.iteritems():
            for n, top in enumerate(topn, 1):
                tmp = {"gameid": gameid, "ds": self.date, "snid": snid, "rank": n}
                tmp.update(top)
                group_list.append(tmp)
        # print("****", group_list)
        ddl.PayRichMultiRoleid.insert(group_list)

    def update_all_role(self, gameid, df):
        """更新all_role表"""

        index = ["openid", "clientid"]
        df_role = self.load_all_role(gameid, index=index)

        # 更新累计消耗
        df_consume = pd.DataFrame(df.groupby(index)["consume_sum"].sum())
        df_role_consume = df_role[["consume_sum"]]
        df_role_consume = df_role_consume.add(df_consume, fill_value=0)
        df_role.update(df_role_consume)

        # 更新own_after, level, vip_level
        df2 = df.drop_duplicates(subset=index, take_last=True)[["openid", "clientid", "own_after", "level", "vip_level"]]
        df2.set_index(index, inplace=True)
        df_role.update(df2)

        # 更新first_pay_level
        # 老数据payment没有level字段，consume表补充
        boolean = df_role.first_payment_time.notnull() & df_role.first_pay_level.isnull()
        df_role_level = df_role[boolean][["first_pay_level"]]
        df_level = df2[["level"]]
        df_level.columns = ["first_pay_level"]
        df_role_level.update(df_level)
        df_role.update(df_role_level)

        self.save_all_role(gameid, df_role)

        # 计算分服留存
        try:
            role_resident = RoleResident(self, gameid, df_role)
            role_resident.process()
        except Exception as e:
            log.error("role client resident error: %s" % str(e))

    def update_all_role_multi_roleid(self, gameid, df):
        """更新all_role表"""
        index = ["openid", "clientid", "roleid"]
        df_role = self.load_all_role_multi_roleid(gameid, index=index)

        # 更新累计消耗
        df_consume = pd.DataFrame(df.groupby(index)["consume_sum"].sum())
        df_role_consume = df_role[["consume_sum"]]
        df_role_consume = df_role_consume.add(df_consume, fill_value=0)
        df_role.update(df_role_consume)

        # 更新own_after, level, vip_level
        df2 = df.drop_duplicates(subset=index, take_last=True)[["openid", "clientid", "roleid", "own_after", "level", "vip_level"]]
        df2.set_index(index, inplace=True)
        df_role.update(df2)

        # 更新first_pay_level
        # 老数据payment没有level字段，consume表补充
        boolean = df_role.first_payment_time.notnull() & df_role.first_pay_level.isnull()
        df_role_level = df_role[boolean][["first_pay_level"]]
        df_level = df2[["level"]]
        df_level.columns = ["first_pay_level"]
        df_role_level.update(df_level)
        df_role.update(df_role_level)

        self.save_all_role_multi_roleid(gameid, df_role)
