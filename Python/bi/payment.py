# coding=utf8

import heapq
import operator

import pandas as pd
import numpy as np
from collections import defaultdict

from .. import config
from .. import ddl
from .. import util
from .. import const
from login import LoginUnit
from resident import Resident
from unit import RelatedUnit


class PaymentUnit(RelatedUnit):
    """支付统计"""
    PR = 4
    TOPN = 500
    RelatedModel = [ddl.PayMent, ddl.Login]
    HISTORY_FIELDS = ["openid", "snid", "payment_time"]
    HISTORY_CSV = "pay_history.csv"
    TMP_PAYMENT_NEW_CSV = "payment_new.csv"
    TMP_PAYRICH_CSV = "pay_rich.csv"
    TMP_PAYRICH_MULTI_ROLEID_CSV = "pay_rich_multi_roleid.csv"

    def process_dataframe(self, gameid, df, login_df):
        if df.empty: return
        df.fillna({"val": 0}, inplace=True)
        group = {
            "gameid": gameid,
            "snid": defaultdict(dict),
            "clientid": defaultdict(dict),
            "all": {},
        }
        self.cal_income(df, group)
        self.cal_pay_cnt(df, group)
        self.cal_fitst_pay_cnt(gameid, df, group, login_df)
        self.cal_max_amount(df, group)
        self.storage(group)
        self.cal_pay_rich(gameid, df)
        self.update_all_role(gameid, df)
        if config.multi_roleid:
            self.update_all_role_multi_roleid(gameid, df)
            self.cal_pay_rich_multi_roleid(gameid, df)

    def cal_income(self, df, group):
        """计算收入
            同一个gameid可能有不同currency,如果amount非空取amount,否则取val
            该逻辑已经放在csv处理阶段，处理后currency肯定为rmb
                pt结构简化如下:
                            amount        val
                clientid     c1 c2 All  c1  c2  All
                snid
                s1            4  4   8  40  40   80
                s2          NaN  2   2 NaN  20   20
                All           4  6  10  40  60  100
        """
        group["currency"] = "rmb"
        self.cal_currency(df, group)

    def cal_currency(self, df, group):
        """统计收入"""
        # 收入透视表
        pt = df.pivot_table(index=["snid"], columns=["clientid"], values=["amount", "val", "openid"], aggfunc={"amount": np.sum, "val": np.sum, "openid": len}, margins=True)
        # 根据平台统计(此时clientid为0)
        # print(pt)
        # r_rate = self.rmb_rate(currency)
        # v_rate = self.val_rate(group["gameid"])

        # def cal_amount(amount, val):
        #     if amount == 0:
        #         amount = val *v_rate
        #     else
        #         amount *= r_rate
        #     return amount

        for snid in pt.index:
            if snid == "All":
                continue
            amount = pt.loc[snid]["amount"]["All"]
            val = pt.loc[snid]["val"]["All"]
            group["snid"][snid]["amount"] = amount
            group["snid"][snid]["val"] = val
            group["snid"][snid]["pay_cnt"] = pt.loc[snid]["openid"]["All"]

        # 根据区服统计(此时snid为0)
        for clientid in pt.columns.get_level_values("clientid").unique():
            if clientid == "All":
                continue
            amount = pt["amount"][clientid]["All"]
            val = pt["val"][clientid]["All"]
            group["clientid"][clientid]["amount"] = amount
            group["clientid"][clientid]["val"] = val
            group["clientid"][clientid]["pay_cnt"] = pt["openid"][clientid]["All"]

        # 总统计(此时snid和clientid均为0)
        amount = pt.loc["All"]["amount"]["All"]
        val = pt.loc["All"]["val"]["All"]
        group["all"]["amount"] = amount
        group["all"]["val"] = val
        group["all"]["pay_cnt"] = pt.loc["All"]["openid"]["All"]

    def cal_pay_cnt(self, df, group, field="user_pay_cnt"):
        """计算付费(首次付费)用户"""
        # 平台用户数量统计
        total = 0
        snid_users = df.groupby("snid").openid.nunique()
        for snid, cnt in snid_users.iteritems():
            total += cnt
            group["snid"][snid][field] = cnt

        # 区服用户数量统计
        clientid_users = df.groupby("clientid").openid.nunique()
        for clientid, cnt in clientid_users.iteritems():
            group["clientid"][clientid][field] = cnt

        # 总统计
        group["all"][field] = total  # df.openid.nunique()

    def cal_fitst_pay_cnt(self, gameid, df, group, login_df):
        """计算首次付费用户"""
        df_history = self.load_history(gameid)
        if df_history.empty:
            self.cal_pay_cnt(df, group, field="first_pay_cnt")
            df_append = df
        else:
            df_history2 = df_history[df_history["payment_time"]<self.pre_date_timestamp]
            df2 = df[~df.openid.isin(df_history2.openid)]
            self.cal_pay_cnt(df2, group, field="first_pay_cnt")
            df_append = df2

        # 计算首次付费总金额
        self.cal_first_amount(df_append, group)

        # 增加新的历史付费记录
        df_unique = df_append.drop_duplicates(subset="openid")[self.HISTORY_FIELDS]

        # 增量更新
        df_append_wr = df_unique[~df_unique["openid"].isin(df_history["openid"])]
        df_append_wr.to_csv(self.history_path(gameid), header=False, index=False, mode='a', encoding="utf8")

        # #全量更新(由于时间所以要去重)
        # df_write = df_history.append(df_unique)
        # df_write.drop_duplicates(subset="openid", inplace=True)
        # df_write.to_csv(self.history_path(gameid), header=False, index=False, mode='w', encoding="utf8")

        # 保存首次付费用户临时表
        self.write_tmp_csv(df_unique, gameid, self.TMP_PAYMENT_NEW_CSV)
        # 写入首次付费用户
        self.load_tmp_mysql(gameid, ddl.AllPayUser, self.TMP_PAYMENT_NEW_CSV)

        # 计算新付费用户付费留存率
        self.cal_redident(gameid, group, df, df_history)
        self.cal_ltv_resident(gameid, group, df, df_history, login_df)

    def cal_first_amount(self, df, group):
        """计算首次付费总金额
        只根据snid统计的可以放在这里
        """
        series = df.groupby("snid").amount.sum()
        total = 0
        for snid, amount in series.iteritems():
            total += amount
            group["snid"][snid]["first_amount"] = amount

        group["all"]["first_amount"] = total

        series_clientid = df.groupby("clientid").amount.sum()
        for clientid, amount in series_clientid.iteritems():
            group["clientid"][clientid]["first_amount"] = amount

    def cal_max_amount(self, df, group):
        """计算分服单用户最高付费金额
        只根据clientid统计的放在这里
        """
        series = df.groupby(["openid", "clientid"]).amount.sum()
        df2 = pd.DataFrame(series)
        df2.reset_index(inplace=True)
        series = df2.groupby("clientid").amount.max()
        all_amount = []
        for clientid, amount in series.iteritems():
            all_amount.append(amount)
            group["clientid"][clientid]["max_amount"] = amount

        group["all"]["max_amount"] = max(all_amount)

    def cal_redident(self, gameid, group, df, df_history):
        """计算新用户付费存留"""
        # 今日新增写入数据库,付费维度为2
        common = {"ds": self.date, "gameid": gameid, "dimension": const.PAY_DIMENSION}
        group_list = []
        field = "first_pay_cnt"
        for snid, values in group["snid"].iteritems():
            tmp = dict(common)
            tmp["snid"] = snid
            tmp["resident_cnt"] = values.get("first_pay_cnt", 0)
            group_list.append(tmp)
        tmp = dict(common)
        tmp["snid"] = 0
        tmp["resident_cnt"] = group["all"][field]
        group_list.append(tmp)
        ddl.RegisterPayResidentDay.insert(group_list)
        rd = Resident(self, common, df, df_history)
        rd.cal_resident()

    def cal_ltv_resident(self, gameid, group, df, df_history, login_df):
        """LTV"""
        history_field = LoginUnit.HISTORY_FIELDS
        history_csv = LoginUnit.HISTORY_LOGIN_CSV
        df_history_login = self.load_history(gameid, field=history_field, history_csv=history_csv)
        boolean = (df_history_login[history_field[2]]>=self.start) & (df_history_login[history_field[2]]<self.end)
        df_register = df_history_login[boolean]
        snid_all = df_register.groupby("snid").apply(len)
        # 今日新增写入数据库,新注册付费维度为3
        common = {"ds": self.date, "gameid": gameid, "dimension": const.LTV_NEWPAY_DIMENSION}
        group_list = []

        # 付费新用户
        new_pay = df[df["openid"].isin(df_register["openid"])]
        snid_pay = new_pay.groupby("snid").amount.sum()
        total = 0
        for snid, amount in snid_pay.iteritems():
            tmp = dict(common)
            total += amount
            tmp["snid"] = snid
            tmp["resident_cnt"] = snid_all.get(snid, 0)
            tmp["resident_d1"] = amount
            group_list.append(tmp)
        tmp = dict(common)
        tmp["snid"] = 0
        tmp["resident_cnt"] = len(df_register)
        tmp["resident_d1"] = total
        group_list.append(tmp)
        ddl.LTVResidentDay.insert(group_list)

        rd = Resident(self, common, df, df_history_login, 60)
        rd.cal_ltv_resident()
        self.cal_newlogin_pay_resident(gameid, df, group_list, login_df, df_history_login, df_register)

    def cal_newlogin_pay_resident(self, gameid, df, group, login_df, df_history_login, df_register):
        """新用户在当天付费的用户留存 login_df  是当天的活跃rolelogin df_history_login 是新用户 df_register 当天新注册用户"""
        df_history_pay = self.load_history(gameid, field=self.HISTORY_FIELDS, history_csv=self.HISTORY_CSV)
        new_pay = df_register[df_register["openid"].isin(df["openid"])]
        # 新注册付费
        common = {"ds": self.date, "gameid": gameid, "dimension": const.NEWLOGIN_PAY_DIMENTION}
        new_pay = new_pay.groupby("snid").openid.nunique()
        group_list = []
        total_newpay = 0
        for snid, count in new_pay.iteritems():
            tmp = dict(common)
            total_newpay += count
            tmp["snid"] = snid
            tmp["resident_cnt"] = count
            group_list.append(tmp)
        tmp = dict(common)
        tmp["snid"] = 0
        tmp["resident_cnt"] = total_newpay
        group_list.append(tmp)

        ddl.RegisterPayResidentDay.insert(group_list)
        rd = Resident(self, common, login_df, (df_history_login, df_history_pay))
        rd.cal_newlogin_pay_resident()

        # 新注册非付费
        common_pay = {"ds": self.date, "gameid": gameid, "dimension": const.NEWLOGIN_NOPAY_DIMENTION}
        no_pay = df_register[~df_register["openid"].isin(df["openid"])]
        no_pay_snid = no_pay.groupby("snid").openid.nunique()
        group_list_nopay = []
        total_nopay = 0
        for snid, count in no_pay_snid.iteritems():
            tmp_nopay = dict(common_pay)
            total_nopay += count
            tmp_nopay["snid"] = snid
            tmp_nopay["resident_cnt"] = count
            group_list_nopay.append(tmp_nopay)
        tmp_nopay = dict(common_pay)
        tmp_nopay["snid"] = 0
        tmp_nopay["resident_cnt"] = total_nopay
        group_list_nopay.append(tmp_nopay)

        ddl.RegisterPayResidentDay.insert(group_list_nopay)
        rd = Resident(self, common_pay, login_df, (df_history_login, df_history_pay))
        rd.cal_newlogin_pay_resident()

    def storage(self, group):
        """入库"""

        group_list = []
        common = {k: group[k] for k in ("currency", "gameid")}
        common["ds"] = self.date

        for snid, values in group["snid"].iteritems():
            tmp = dict(common)
            tmp["snid"] = snid
            tmp["clientid"] = 0
            tmp.update(values)
            group_list.append(tmp)

        for clientid, values in group["clientid"].iteritems():
            tmp = dict(common)
            tmp["clientid"] = clientid
            tmp["snid"] = 0
            tmp.update(values)
            group_list.append(tmp)

        # 统计总和
        tmp = dict(common)
        tmp["clientid"] = 0
        tmp["snid"] = 0
        tmp.update(group["all"])
        group_list.append(tmp)
        self.total_group.extend(group_list)
        # print(group_list)
        # print(group)

        ddl.PayDay.insert(group_list)

    def process_total(self, df):
        """处理全game分平台分区服统计"""
        # print(self.total_group)
        # print(df)
        df.fillna({"max_amount": 0}, inplace=True)
        group_list = []
        columns = df.columns.tolist()
        exclude = ["ds", "gameid", "currency", "snid"]
        common = {"ds": self.date, "gameid": 0, "currency": "rmb"}

        # 统计全game全平台(和全game全区服一致)
        boolean = (df["snid"]==0) & (df["clientid"]==0)
        df_total = df[boolean]
        fields = util.remove_multi(columns, *exclude)
        total = df_total[fields].sum()
        tmp = dict(common)
        tmp["snid"] = 0
        tmp["clientid"] = 0
        tmp.update(total.to_dict())
        group_list.append(tmp)

        # #统计全game分平台
        boolean = (df["snid"]!=0) & (df["clientid"]==0)
        df_snid = df[boolean]
        snid_fields = util.remove_multi(columns, *exclude[:-1])
        snid_total = df_snid[snid_fields].groupby("snid").sum()
        for i, snid in enumerate(snid_total.index):
            tmp = dict(common)
            tmp["snid"] = snid
            tmp.update(snid_total.iloc[i].to_dict())
            group_list.append(tmp)

        # 统计全game分区服(没有意义，分服只按游戏统计)
        # boolean = (df["clientid"]!=0) & (df["snid"]==0)
        # df_clientid = df[boolean]
        # clientid_fields = util.remove_multi(columns, *exclude[:-1])
        # clientid_total = df_clientid[clientid_fields].groupby("clientid").sum()
        # for i, clientid in enumerate(clientid_total.index):
        #     tmp = dict(common)
        #     tmp["clientid"] = clientid
        #     tmp.update(clientid_total.iloc[i].to_dict())
        #     group_list.append(tmp)

        # print(group_list)

        ddl.PayDay.insert(group_list)

    def cal_pay_rich(self, gameid, df):
        """计算富豪榜"""
        group = defaultdict(list)
        all_role = []
        df2 = df.groupby(["openid", "clientid", "snid"])["amount", "val"].sum()
        df3 = df2.reset_index()
        df4 = df3.groupby("snid").apply(lambda g: g.sort_index(by="amount", ascending=False).head(self.TOPN))

        self.write_tmp_csv(df4, gameid, self.TMP_PAYRICH_CSV)
        return
        # 需要comsume_sum的统计(见comsume)
        for (snid, _), openid, clientid, _, amount, val in df4.itertuples():
            tmp = {"openid": openid, "clientid": clientid, "amount": amount, "val": val}
            all_role.append(tmp)
            group[snid].append(tmp)

        # 所有平台TOPN名
        group[0] = heapq.nlargest(self.TOPN, all_role, key=operator.itemgetter("amount"))

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
        """计算富豪榜"""
        # 老的游戏在payment中并没有上报roleid
        df2 = df.groupby(["openid", "clientid", "roleid", "snid"])["amount", "val"].sum()
        df3 = df2.reset_index()
        df4 = df3.groupby("snid").apply(lambda g: g.sort_index(by="amount", ascending=False).head(self.TOPN))

        self.write_tmp_csv(df4, gameid, self.TMP_PAYRICH_MULTI_ROLEID_CSV)

    def update_all_role(self, gameid, df):
        """更新all_role表"""
        # payment旧日志没有roleid字段，使用openid+clientid代替
        columns = ["openid", "clientid", "payment_time", "level"]
        df_role = self.load_all_role(gameid, index=columns[:2])
        # 更新累计金额和货币
        df_amount = df.groupby(columns[:2])["amount", "val"].sum()
        df_role_amount = df_role[["amount", "val"]]
        df_role_amount = df_role_amount.add(df_amount, fill_value=0)
        df_role.update(df_role_amount)

        df_pay = df.drop_duplicates(subset=columns[:2])[columns]
        df_pay.set_index(columns[:2], inplace=True)
        # 更新last_payment_time
        df_time = df_pay[columns[2:-1]]
        df_time.columns = ["last_payment_time"]
        df_role.update(df_time)

        # 更新first_payment_time
        boolean = df_role["first_payment_time"].isnull()
        df_role_time = df_role[boolean][["first_payment_time"]]
        df_time.columns = ["first_payment_time"]
        df_role_time.update(df_time)
        df_role.update(df_role_time)

        # 更新vip_level
        df_vip_level = df.drop_duplicates(subset=columns[:2], take_last=True)[["openid", "clientid", "vip_level"]]
        df_vip_level.set_index(columns[:2], inplace=True)
        df_role.update(df_vip_level)

        # 更新first_pay_level
        boolean = df_role["first_pay_level"].isnull()
        df_role_level = df_role[boolean][["first_pay_level"]]
        df_level = df_pay[columns[3:]]
        df_level.columns = ["first_pay_level"]
        df_role_level.update(df_level)
        df_role.update(df_role_level)

        self.save_all_role(gameid, df_role)

    def update_all_role_multi_roleid(self, gameid, df):
        """更新all_role表"""
        # payment旧日志没有roleid字段，使用openid+clientid代替
        columns = ["openid", "clientid", "roleid", "payment_time", "level"]
        df_role = self.load_all_role_multi_roleid(gameid, index=columns[:3])
        # 更新累计金额和货币
        df_amount = df.groupby(columns[:3])["amount", "val"].sum()
        df_role_amount = df_role[["amount", "val"]]
        df_role_amount = df_role_amount.add(df_amount, fill_value=0)
        df_role.update(df_role_amount)

        df_pay = df.drop_duplicates(subset=columns[:3])[columns]
        df_pay.set_index(columns[:3], inplace=True)
        # 更新last_payment_time
        df_time = df_pay[columns[3:-1]]
        df_time.columns = ["last_payment_time"]
        df_role.update(df_time)

        # 更新first_payment_time
        boolean = df_role["first_payment_time"].isnull()
        df_role_time = df_role[boolean][["first_payment_time"]]
        df_time.columns = ["first_payment_time"]
        df_role_time.update(df_time)
        df_role.update(df_role_time)

        # 更新vip_level
        df_vip_level = df.drop_duplicates(subset=columns[:3], take_last=True)[["openid", "clientid", "roleid", "vip_level"]]
        df_vip_level.set_index(columns[:3], inplace=True)
        df_role.update(df_vip_level)

        # 更新first_pay_level
        boolean = df_role["first_pay_level"].isnull()
        df_role_level = df_role[boolean][["first_pay_level"]]
        df_level = df_pay[columns[4:]]
        df_level.columns = ["first_pay_level"]
        df_role_level.update(df_level)
        df_role.update(df_role_level)

        self.save_all_role_multi_roleid(gameid, df_role)
