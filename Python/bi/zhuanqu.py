# coding=utf8

from .. import ddl
from unit import Unit


class ZhuanquUnit(Unit):
    """转区"""
    Model = ddl.Zhuanqu

    def process_dataframe(self, gameid, df):
        self.change_clientid(df, gameid)

    def change_clientid(self, df, gameid):
        """转区"""
        df2 = df.groupby(["src", "dst"])
        index = ["openid", "clientid"]
        clientid_kv = dict([k for k, v in df2])

        all_role = self.load_all_role(gameid)
        df.set_index(["openid", "src"], inplace=True)

        boolean = all_role.index.isin(df.index)
        all_role2 = all_role[~boolean]
        all_drop = all_role[boolean]
        if all_drop.empty:
            return
        all_drop.reset_index(inplace=True)
        all_drop.clientid = all_drop.clientid.apply(lambda x: clientid_kv[x])
        # apply可能会修改合适的dtype
        all_drop.clientid = all_drop.clientid.astype(int)

        # 增加修改后的用户
        columns = ["amount", "val", "consume_sum"]
        all_drop2_update = all_drop.groupby(index)["amount", "val", "consume_sum"].sum()
        all_drop2 = all_drop.drop_duplicates(subset=index).set_index(index)
        all_drop2.update(all_drop2_update)

        # 已有的累加
        all_role_sum = all_role2[columns].add(all_drop2[columns], fill_value=0)
        all_role2.update(all_role_sum)
        all_role_append = all_drop2[~all_drop2.index.isin(all_role2.index)]
        all_role2 = all_role2.append(all_role_append)

        self.save_all_role(gameid, all_role2)
