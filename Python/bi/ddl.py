# coding=utf8

from functools import partial

import torndb

import config
from log import log

"""
数据库定义
"""


class DDL(object):
    TABLES = {}
    OLD_TABLES = {}
    NEW_TABLES = {}
    CONNECTIONS = {}

    @classmethod
    def connection(cls, db):
        """默认为统计的库
        db config.DB_ANALYSE, config.DB_STORE
        """
        if db not in cls.CONNECTIONS:
            get = partial(config.get, db)
            log.warning("mysql connection init, db: %s", db)
            conn = torndb.Connection(get("host"), get("db"), user=get("user"), password=get("password"))
            cls.CONNECTIONS[db] = conn
            return conn
        return cls.CONNECTIONS[db]

    @classmethod
    def execute(cls, sql, db):
        try:
            cls.connection(db).execute(sql)
        except Exception as e:
            log.error("DDL execute error: %s, db: %s, sql:\n%s", str(e), db, sql)

    @classmethod
    def create(cls, table, gameid=None, date=None):
        model = cls.TABLES.get(table)
        if model is None:
            log.error("DDL create error: model is None")
            return None
        if gameid is not None and model.NEED_GAMEID:
            if date is not None:
                table = "{0}_{1}_{2}".format(gameid, table, date)
            else:
                table = "{0}_{1}".format(gameid, table)

        try:
            desc_sql = '''desc `{0}`'''.format(table)
            cls.connection(model.DB).execute(desc_sql)
        except Exception as e:
            log.warning(e)
            fmt = '''create table if not exists `{0}`({1}'''.format(table, model.CREATE_SQL)
            cls.connection(model.DB).execute(fmt)
            log.info("table %s is created." % table)
        else:
            # log.info("table %s is already exist." % table)
            pass
        return True

    @classmethod
    def insert(cls, table, groupdict, gameid=None):
        model = cls.TABLES[table]
        model.insert(groupdict, gameid)

    @classmethod
    def mysql_load_data(cls, table, csv, gameid=None, db=None, ignore="", field=None, date=None):
        if isinstance(table, str):
            model = cls.TABLES.get(table)
        else:
            model = table

        if model is None:
            log.error("DDL create error: model is None")
            return ""

        get = partial(config.get, model.DB)
        if db is None:
            db = get("db")
        password = get("password")
        if password != "":
            passwd = "-p{0}".format(password)
        else:
            passwd = ""
        table = model.TABLE_NAME
        cls.create(table, gameid, date)

        if gameid is not None and model.NEED_GAMEID:
            if date is not None:
                table = "{0}_{1}_{2}".format(gameid, table, date)
            else:
                table = "{0}_{1}".format(gameid, table)

        fields = field or model.FIELDS
        if ignore:
            ignore = "ignore {0} lines".format(ignore)

        cmd = '''mysql -u{0} {1} -h {2} {3} --local-infile=1 -e "load data local infile '{4}' ignore into table \`{5}\` \
            character set utf8 fields terminated by ',' optionally enclosed by '\\"' escaped by '\\"' \
            lines terminated by '\\n' {6} ({7});"\
            '''.format(get("user"), passwd, get("host"), db, csv, table, ignore, ','.join(fields))

        return cmd


class TableMeta(type):
    def __init__(cls, classname, bases, dict_):
        assert hasattr(cls, "TABLE_NAME")
        if classname in ("Model", "Merge"):
            return type.__init__(cls, classname, bases, dict_)

        table = getattr(cls, "TABLE_NAME")
        instance = cls()
        if table in DDL.TABLES:
            # may two class has the same TABLE_NAME, just warning
            print("[warning] duplicate table template:{0}, class:{1}".format(table, classname))
        else:
            DDL.TABLES[table] = instance

        if hasattr(cls, "OLDBI_TABLE"):
            DDL.OLD_TABLES[getattr(cls, "OLDBI_TABLE")] = instance
        if hasattr(cls, "NEWBI_TABLE"):
            DDL.NEW_TABLES[getattr(cls, "NEWBI_TABLE")] = instance
        if hasattr(cls, "CREATE_SQL"):
            fields = check_fields(getattr(cls, "CREATE_SQL"))
            setattr(cls, "FIELDS", fields)

        return type.__init__(cls, classname, bases, dict_)


def check_fields(sql):
    """ get table fields from create sql """
    fields = []
    for line in sql.splitlines():
        row = line.strip()
        if row[0] != '`' or "AUTO_INCREMENT" in row:
            continue
        fields.append(row.split('`', 2)[1])

    return fields


def format_sql(group, fields):
    values = ["'{0}'".format(group.get(f, 0)) for f in fields]
    return "({0})".format(','.join(values))


class Model(object):
    __metaclass__ = TableMeta
    TABLE_NAME = ""        # 数据库表名
    OLDBI_TABLE = ""       # 老日记对应
    NEWBI_TABLE = ""       # 新日志对应
    CREATE_SQL = ""
    DEFAULTS = {}          # 字段默认值
    TIMESTAMP = ""         # 时间字段(方便老日志date+time合并为timestamp)
    NEED_GAMEID = True     # 是否是一个gameid一张表(只有统计表不是)
    DB = config.DB_STORE   # model默认是入库的库
    Dtype = {"roleid": str, "openid": str, "clientid": int}
    CLIENT_SPLIT = False   # 是否按区服分割数据
    STORE = True           # 是否入库

    @classmethod
    def table_name(cls, gameid=None):
        table = cls.TABLE_NAME
        if gameid is not None and cls.NEED_GAMEID:
            table = "{0}_{1}".format(gameid, table)
        return table

    @classmethod
    def insert(cls, groupdict, gameid=None):
        bucket = 50
        if not groupdict:
            return
        DDL.create(cls.TABLE_NAME, gameid)
        if isinstance(groupdict, (list, tuple)):
            values = []
            while groupdict:
                part_sql = ','.join([format_sql(group, cls.FIELDS) for group in groupdict[:bucket]])
                values.append(part_sql)
                groupdict = groupdict[bucket:]
        else:
            values = [format_sql(groupdict, cls.FIELDS)]

        table = cls.table_name(gameid)
        for value in values:
            sql = """insert into {0}({1}) values{2}""".format(table, ','.join(cls.FIELDS), value)
            try:
                DDL.connection(cls.DB).execute(sql)
            except Exception as e:
                log.error("table:%s insert error, %s, sql:\n%s", table, str(e), sql)

    @classmethod
    def query(cls, sql):
        return DDL.connection(cls.DB).query(sql)

    @classmethod
    def execute(cls, sql):
        return DDL.execute(sql, cls.DB)

    @classmethod
    def drop(cls, gameid=None):
        """删除表"""
        sql = """drop table if exists {0}"""
        sql = sql.format(cls.table_name(gameid))
        print(sql)
        cls.execute(sql)

    @classmethod
    def delete(cls, gameids, **where):
        if not isinstance(gameids, (list, tuple, set)):
            gameids = [gameids]
        # where_clause = " and ".join("{0}='{1}'".format(k, v) for k, v in where.iteritems())
        where_clause = " and ".join("{0}='{1}'".format(k, v) if not isinstance(v, (list, tuple, set)) else "{0} in({1})".format(k, ",".join(map(str, v))) for k, v in where.iteritems())
        sql = """delete from {0} where {1} and gameid in({2})"""
        sql = sql.format(cls.table_name(), where_clause, ",".join(gameids))
        # print(sql)
        cls.execute(sql)

    @classmethod
    def update(cls, groupdict, where, gameid=None):
        if isinstance(groupdict, dict):
            groupdict = [groupdict]
        table = cls.table_name(gameid)
        for group in groupdict:
            where_clause = " and ".join(["{0}='{1}'".format(f, group[f]) for f in where])
            sql = """select 1 from {0} where {1}""".format(table, where_clause)
            raw_count = DDL.connection(cls.DB).execute_rowcount(sql)
            if raw_count < 1:
                cls.insert(group, gameid=gameid)
            else:
                values = ",".join(["{0}='{1}'".format(f, group[f]) for f in group.keys() if f not in where])
                sql = """update {0} set {1} where {2}""".format(table, values, where_clause)
                try:
                    DDL.connection(cls.DB).execute_rowcount(sql)
                except Exception as e:
                    log.error("table:%s update error,%s, sql:\n%s", table, str(e), sql)


class Merge(Model):
    """ 统计表 """
    NEED_GAMEID = False
    DB = config.DB_ANALYSE    # model默认使用统计的库


_all_user_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `login_time` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `openid_snid` (`openid`,`snid`),
  KEY `login_time` (`login_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='所有用户表' '''
class AllUser(Model):
    TABLE_NAME = "all_user"
    CREATE_SQL = _all_user_sql


_all_pay_user_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `payment_time` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `openid_snid` (`openid`,`snid`),
  KEY `payment_time` (`payment_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='所有用户首次充值表' '''
class AllPayUser(Model):
    TABLE_NAME = "all_pay_user"
    CREATE_SQL = _all_pay_user_sql


_all_advice_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `MAC` varchar(100) NOT NULL COMMENT '用户平台账号',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `login_time` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `mac_snid` (`MAC`,`snid`),
  KEY `login_time` (`login_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='所有设备表' '''
class AllAdvice(Model):
    TABLE_NAME = "all_advice"
    CREATE_SQL = _all_advice_sql


_all_role_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `rolename` varchar(100) DEFAULT NULL,
  `school` varchar(64) DEFAULT NULL COMMENT '角色门派',
  `IP` varchar(64) DEFAULT NULL,
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `rolelogin_time` int(11) NOT NULL COMMENT '建角时间',
  `amount` int(11) NOT NULL DEFAULT 0 COMMENT '金额',
  `val` int(11) NOT NULL DEFAULT 0 COMMENT '购买的游戏币(元宝 、钻石)数量',
  `consume_sum` int(11) NOT NULL DEFAULT 0 COMMENT '消耗钻石数',
  `own_after` int(11) NOT NULL DEFAULT 0 COMMENT '消耗后剩余钻石数',
  `first_payment_time` int(11) DEFAULT NULL COMMENT '最初支付时间戳',
  `last_payment_time` int(11) DEFAULT NULL COMMENT '最后支付时间戳',
  `last_login_time` int(11) DEFAULT NULL COMMENT '最后活跃时间戳',
  `first_pay_level` smallint(6) NOT NULL DEFAULT 0 COMMENT '首次付费等级',
  `level` smallint(6) NOT NULL DEFAULT 0 COMMENT '当前等级',
  `vip_level` smallint(6) NOT NULL DEFAULT 0 COMMENT '当前vip等级',
  PRIMARY KEY (`id`),
  UNIQUE KEY `openid_clientid` (`openid`,`clientid`),
  KEY `amount_snid` (`amount`,`snid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='所有角色表' '''
class AllRole(Model):
    TABLE_NAME = "all_role"
    CREATE_SQL = _all_role_sql
    DB = config.DB_ANALYSE    # 富豪榜需要所有角色信息,所以需放到统计表


_all_role_multi_roleid_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `rolename` varchar(100) DEFAULT NULL,
  `school` varchar(64) DEFAULT NULL COMMENT '角色门派',
  `IP` varchar(64) DEFAULT NULL,
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `rolelogin_time` int(11) NOT NULL COMMENT '建角时间',
  `amount` int(11) NOT NULL DEFAULT 0 COMMENT '金额',
  `val` int(11) NOT NULL DEFAULT 0 COMMENT '购买的游戏币(元宝 、钻石)数量',
  `consume_sum` int(11) NOT NULL DEFAULT 0 COMMENT '消耗钻石数',
  `own_after` int(11) NOT NULL DEFAULT 0 COMMENT '消耗后剩余钻石数',
  `first_payment_time` int(11) DEFAULT NULL COMMENT '最初支付时间戳',
  `last_payment_time` int(11) DEFAULT NULL COMMENT '最后支付时间戳',
  `last_login_time` int(11) DEFAULT NULL COMMENT '最后活跃时间戳',
  `first_pay_level` smallint(6) NOT NULL DEFAULT 0 COMMENT '首次付费等级',
  `level` smallint(6) NOT NULL DEFAULT 0 COMMENT '当前等级',
  `vip_level` smallint(6) NOT NULL DEFAULT 0 COMMENT '当前vip等级',
  PRIMARY KEY (`id`),
  UNIQUE KEY `openid_clientid_roleid` (`openid`,`clientid`, `roleid`),
  KEY `amount_snid` (`amount`,`snid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='所有角色表' '''
class AllRoleMultiRoleid(Model):
    TABLE_NAME = "all_role_multi_roleid"
    CREATE_SQL = _all_role_multi_roleid_sql
    DB = config.DB_ANALYSE    # 富豪榜需要所有角色信息,所以需放到统计表


_account_sql = '''\
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `accountid` varchar(100) NOT NULL COMMENT '账号ID',
  `rolelist_size` int(11) NOT NULL COMMENT '角色列表个数',
  `cents_add` int(11) NOT NULL COMMENT '充值金额（分）',
  `cash_add` int(11) NOT NULL COMMENT '充值增加的金钻',
  `cash_total` int(11) NOT NULL COMMENT '金钻总数',
  `create_time` int(11) NOT NULL COMMENT '角色创建时间戳',
  `login_time` int(11) NOT NULL COMMENT '最后登录时间',
  `level` smallint(6) NOT NULL COMMENT '主账号等级',
  `vip_level` smallint(6) NOT NULL COMMENT 'VIP等级',
  UNIQUE KEY `accountid_clientid` (`accountid`,`clientid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='快照账号表' '''
class Account(Model):
    TABLE_NAME = "account"
    CREATE_SQL = _account_sql


_role_sql = '''\
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `roleid` varchar(64) NOT NULL COMMENT '角色ID',
  `accountid` varchar(100) NOT NULL COMMENT '账号ID',
  `name` varchar(100) NOT NULL COMMENT '角色名',
  `status` smallint(6) NOT NULL COMMENT '角色状态（是否删除）',
  `create_time` int(11) NOT NULL COMMENT '角色创建时间戳',
  `delete_time` int(11) NOT NULL COMMENT '角色删除时间戳',
  `lastlogin_time` int(11) NOT NULL COMMENT '上次登录时间戳',
  `bind_cash` int(11) NOT NULL COMMENT '绑定钻数量',
  `money` bigint(20) NOT NULL COMMENT '金币数量',
  `level` smallint(6) NOT NULL COMMENT '主账号等级',
  `vip_level` smallint(6) NOT NULL COMMENT 'VIP等级',
  `exp` bigint(20) NOT NULL COMMENT '经验',
  `time_used` int(11) NOT NULL COMMENT '角色总在线时长',
  UNIQUE KEY `roleid_accountid_clientid` (`accountid`,`clientid`,`roleid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='快照角色表' '''
class Role(Model):
    TABLE_NAME = "role"
    CREATE_SQL = _role_sql


_guild_sql = '''\
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '渠道ID',
  `name` varchar(100) NOT NULL COMMENT '帮会名称',
  `max_num` int(11) NOT NULL COMMENT '帮会最大人数',
  `new_num` int(11) NOT NULL COMMENT '帮会现有人数',
  `act_num` int(11) DEFAULT NULL COMMENT '活跃人数',
  `force_dline` int(11) DEFAULT NULL COMMENT '截止时间总战力',
  `list_rank` int(11) DEFAULT NULL COMMENT '帮会排行榜排名',
  `master_name` varchar(100) NOT NULL COMMENT '帮主名称',
  `level` int(11) DEFAULT NULL COMMENT '帮会等级',
  `master_level` int(11) DEFAULT NULL COMMENT '帮主等级',
  `contr_total` int(11) DEFAULT NULL COMMENT '帮会贡献总量',
  `contr_day` bigint(20) DEFAULT NULL COMMENT '今日贡献量',
  `contr_num` bigint(20) DEFAULT NULL COMMENT '今日贡献人数',
  KEY `clientid` (`clientid`),
  KEY `force_dline` (`force_dline`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='快照工会统计表' '''
class Guild(Model):
    TABLE_NAME = "guild"
    CREATE_SQL = _guild_sql


_login_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `device` varchar(50) DEFAULT NULL,
  `OS` varchar(50) DEFAULT NULL COMMENT '系统信息',
  `MAC` varchar(100) DEFAULT NULL COMMENT '设备号',
  `login_time` int(11) DEFAULT NULL,
  `ds` date NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ds_openid` (`openid`,`ds`),
  KEY `login_time` (`login_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='用户登录明细表' '''
class Login(Model):
    TABLE_NAME = "user_login_log"
    OLDBI_TABLE = "login"
    NEWBI_TABLE = "login"
    CREATE_SQL = _login_sql


_role_new_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `rolename` varchar(100) DEFAULT NULL,
  `school` varchar(64) DEFAULT NULL COMMENT '角色门派',
  `rolelogin_time` int(11) NOT NULL COMMENT '建角时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `clientid_openid` (`openid`, `clientid`),
  KEY `rolelogin_time` (`rolelogin_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='角色创建表' '''
class RoleNew(Model):
    TABLE_NAME = "role_register_log"
    OLDBI_TABLE = "install"
    NEWBI_TABLE = "role_new"
    CREATE_SQL = _role_new_sql


_role_login_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `type` smallint(6) DEFAULT NULL,
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `online_time` int(11) DEFAULT NULL COMMENT '本次在线时长',
  `rolelogin_time` int(11) NOT NULL,
  `ds` date NOT NULL,
  PRIMARY KEY (`id`),
  KEY `rolelogin_time` (`rolelogin_time`),
  UNIQUE KEY `roleid_ds_type` (`roleid`, `ds`, `clientid`, `type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='角色登录明细表' '''
class RoleLogin(Model):
    TABLE_NAME = "role_login"
    OLDBI_TABLE = "role_login"
    NEWBI_TABLE = "role_login"
    CREATE_SQL = _role_login_sql
    TIMESTAMP = "rolelogin_time"
    DEFAULTS = {"type": 1, "online_time": 0}


class RoleLogout(Model):
    TABLE_NAME = "role_login"
    OLDBI_TABLE = "role_logout"
    NEWBI_TABLE = ""
    CREATE_SQL = _role_login_sql
    TIMESTAMP = "rolelogin_time"
    DEFAULTS = {"type": 2}


_levelup_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `kingdom` smallint(6) DEFAULT NULL COMMENT '1=打怪升级2=使用道具3=活动4=领奖5=打坐6=其他7=任务',
  `levelup_time` int(11) DEFAULT NULL COMMENT '升级时间戳',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='升级' '''
class Levelup(Model):
    TABLE_NAME = "levelup"
    OLDBI_TABLE = "levelup"
    NEWBI_TABLE = "levelup"
    CREATE_SQL = _levelup_sql


_zhuanqu_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `src` int(11) NOT NULL COMMENT '原区服ID',
  `dst` int(11) NOT NULL COMMENT '目标区服ID',
  `ds` date DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='转区' '''
class Zhuanqu(Model):
    TABLE_NAME = "zhuanqu"
    OLDBI_TABLE = "zhuanqu"
    NEWBI_TABLE = "zhuanqu"
    CREATE_SQL = _zhuanqu_sql


_online_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `online_time` int(11) NOT NULL,
  `users` int(11) DEFAULT NULL COMMENT '当日活跃用户在线数',
  PRIMARY KEY (`id`),
  KEY `online_time` (`online_time`),
  KEY `dx1` (`gameid`,`clientid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='实时在线' '''
class Online(Model):
    TABLE_NAME = "user_online_log"
    OLDBI_TABLE = "online"
    NEWBI_TABLE = "online"
    CREATE_SQL = _online_sql


_payment_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `vip_level` smallint(6) DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL COMMENT '金额',
  `currency` varchar(10) DEFAULT NULL COMMENT '货币类型',
  `val` int(11) DEFAULT NULL COMMENT '购买的游戏币(元宝 、钻石)数量',
  `transactionid` varchar(200) DEFAULT NULL COMMENT '订单号',
  `payment_time` int(11) NOT NULL COMMENT '支付时间戳',
  PRIMARY KEY (`id`),
  KEY `dx1` (`gameid`,`clientid`,`snid`,`openid`,`roleid`),
  KEY `payment_time` (`payment_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='充值明细表' '''
class PayMent(Model):
    TABLE_NAME = "pay_orders"
    OLDBI_TABLE = "payment"
    NEWBI_TABLE = "payment"
    CREATE_SQL = _payment_sql


_consume_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `vip_level` smallint(6) DEFAULT NULL,
  `consume_time` int(11) NOT NULL COMMENT '消耗时间戳',
  `consume_sum` int(11) DEFAULT NULL COMMENT '消耗钻石数',
  `own_after` int(11) DEFAULT NULL COMMENT '消耗后剩余钻石数',
  `goodsid` varchar(64) NOT NULL COMMENT '物品ID',
  `goodsprice` decimal(10,2) DEFAULT NULL COMMENT '物品单价',
  `goodsnum` int(11) DEFAULT NULL COMMENT '物品数量',
  PRIMARY KEY (`id`),
  KEY `dx1` (`gameid`,`clientid`,`snid`,`openid`,`roleid`),
  KEY `goodsid` (`goodsid`),
  KEY `consume_time` (`consume_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='消耗表' '''
class Consume(Model):
    TABLE_NAME = "consume"
    OLDBI_TABLE = "consume"
    NEWBI_TABLE = "consume"
    CREATE_SQL = _consume_sql


_mission_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `vip_level` smallint(6) DEFAULT NULL,
  `mission_time` int(11) NOT NULL COMMENT '时间戳',
  `mission_type` int(11) DEFAULT NULL COMMENT '关卡=1，任务=2，副本=3',
  `mission_level` varchar(32) DEFAULT NULL COMMENT '普通、精英或低级、中级、高级或某地图',
  `event_name` varchar(64) DEFAULT NULL COMMENT '（任务、关卡、副本）名称',
  `event_ID` varchar(32) DEFAULT NULL COMMENT '（任务、关卡、副本）ID',
  `event_OK` smallint(6) DEFAULT NULL COMMENT '是否成功，成功1，不成功2',
  PRIMARY KEY (`id`),
  KEY `dx1` (`gameid`,`clientid`,`snid`,`openid`,`roleid`),
  KEY `event_id` (`event_id`),
  KEY `mission_time` (`mission_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='任务表' '''
class Mission(Model):
    TABLE_NAME = "mission"
    OLDBI_TABLE = "mission"
    NEWBI_TABLE = "mission"
    CREATE_SQL = _mission_sql


class ClientSplitModel(Model):
    """按服切割数据"""
    CLIENT_SPLIT = True
    STORE = False


_props_get_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `vip_level` smallint(6) DEFAULT NULL,
  `get_time` int(11) NOT NULL COMMENT '时间戳',
  `get_sum` int(11) DEFAULT NULL COMMENT '本次获得该道具数量',
  `own_after` int(11) DEFAULT NULL COMMENT '剩余该道具的总数量',
  `propsid` varchar(200) NOT NULL COMMENT '道具ID',
  `get_wayid` int(11) NOT NULL COMMENT '获得方式',
  `get_wayclassid` int(11) NOT NULL COMMENT '获得方式所属分类(任务，拍卖行)',
  `type` varchar(200) NOT NULL COMMENT '道具特征(bind，unbind)',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  `extend_2` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `get_time` (`get_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='道具产出表' '''
class PropsGet(ClientSplitModel):
    TABLE_NAME = "props_get"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _props_get_sql


_props_get_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `dimension` smallint(6) DEFAULT NULL COMMENT 'dau1,新用户2,首付费3,流水4,历史付费7',
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `propsid` varchar(200) NOT NULL COMMENT '道具ID',
  `type` varchar(200) NOT NULL COMMENT '道具特征(bind，unbind)',
  `get_wayid` int(11) NOT NULL COMMENT '获得方式',
  `get_wayclassid` int(11) NOT NULL COMMENT '获得方式所属分类(任务，拍卖行)',
  `total_cnt` int(11) NOT NULL COMMENT '人次',
  `unique_cnt` int(11) NOT NULL COMMENT '人数',
  `props_sum` int(11) NOT NULL COMMENT '获取道具总数量',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`dimension`, `clientid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='道具产出表' '''
class PropsGetDay(Merge):
    TABLE_NAME = "props_get_day"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _props_get_day_sql


_props_consume_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `vip_level` smallint(6) DEFAULT NULL,
  `consume_time` int(11) NOT NULL COMMENT '时间戳',
  `consume_sum` int(11) DEFAULT NULL COMMENT '本次消耗该道具数量',
  `own_after` int(11) DEFAULT NULL COMMENT '剩余该道具的总数量',
  `propsid` varchar(200) NOT NULL COMMENT '道具ID',
  `consume_wayid` int(11) NOT NULL COMMENT '获得方式',
  `consume_wayclassid` int(11) NOT NULL COMMENT '获得方式所属分类(任务，拍卖行)',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  `extend_2` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `consume_time` (`consume_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='道具消耗表' '''
class PropsConsume(ClientSplitModel):
    TABLE_NAME = "props_consume"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _props_consume_sql


_gold_get_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `vip_level` smallint(6) DEFAULT NULL,
  `get_time` int(11) NOT NULL COMMENT '时间戳',
  `gold_sum` int(11) DEFAULT NULL COMMENT '本次获得金币数量',
  `gold_total` int(11) DEFAULT NULL COMMENT '目前金币总数量',
  `poundage` int(11) NOT NULL COMMENT '手续费(拍卖行购买物品需交手续费)',
  `get_wayid` int(11) NOT NULL COMMENT '获得方式',
  `get_wayclassid` int(11) NOT NULL COMMENT '获得方式所属分类(任务，拍卖行)',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  `extend_2` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `get_time` (`get_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='金币产出表' '''
class GoldGet(ClientSplitModel):
    TABLE_NAME = "gold_get"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _gold_get_sql


_gold_get_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `dimension` smallint(6) DEFAULT NULL COMMENT 'dau1,新用户2,首付费3,流水4,历史付费7',
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `get_wayid` int(11) NOT NULL COMMENT '获得方式',
  `get_wayclassid` int(11) NOT NULL COMMENT '获得方式所属分类(任务，拍卖行)',
  `total_cnt` bigint(20) NOT NULL COMMENT '人次',
  `unique_cnt` int(11) NOT NULL COMMENT '人数',
  `gold_sum` bigint(20) NOT NULL COMMENT '获取金币总数量',
  `poundage` bigint(20) NOT NULL COMMENT '手续费总数量',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`dimension`, `clientid`, `get_wayclassid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='金币产出日统计表' '''
class GoldGetDay(Merge):
    TABLE_NAME = "gold_get_day"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _gold_get_day_sql


_gold_consume_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `vip_level` smallint(6) DEFAULT NULL,
  `consume_time` int(11) NOT NULL COMMENT '时间戳',
  `gold_sum` int(11) DEFAULT NULL COMMENT '本次消耗金币数量',
  `gold_total` int(11) DEFAULT NULL COMMENT '剩余金币总数量',
  `poundage` int(11) NOT NULL COMMENT '手续费(拍卖行购买物品需交手续费)',
  `consume_wayid` int(11) NOT NULL COMMENT '消耗方式(装备升级)',
  `consume_wayclassid` int(11) NOT NULL COMMENT '消耗的用处',
  `goodsid` varchar(100) NOT NULL COMMENT '物品ID',
  `goodsprice` decimal(10,2) DEFAULT NULL COMMENT '物品单价',
  `goodsnum` int(11) DEFAULT NULL COMMENT '物品数量',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  `extend_2` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `consume_time` (`consume_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='道具消耗表' '''
class GoldConsume(ClientSplitModel):
    TABLE_NAME = "gold_consume"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _gold_consume_sql


_gold_consume_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `dimension` smallint(6) DEFAULT NULL COMMENT 'dau1,新用户2,首付费3,流水4,历史付费7',
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `goodsid` varchar(100) NOT NULL COMMENT '物品',
  `consume_wayid` int(11) NOT NULL COMMENT '获得方式',
  `consume_wayclassid` int(11) NOT NULL COMMENT '获得方式所属分类(任务，拍卖行)',
  `total_cnt` bigint(20) NOT NULL COMMENT '人次',
  `unique_cnt` int(11) NOT NULL COMMENT '人数',
  `gold_sum` bigint(20) NOT NULL COMMENT '获取金币总数量',
  `poundage` bigint(20) NOT NULL COMMENT '手续费总数量',
  `goodsnum` bigint(20) NOT NULL COMMENT '物品总数量',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`dimension`, `clientid`, `goodsid`, `consume_wayclassid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='金币消耗日统计表' '''
class GoldConsumeDay(Merge):
    TABLE_NAME = "gold_consume_day"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _gold_consume_day_sql


_gold_vipconsume_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `dimension` smallint(6) DEFAULT NULL COMMENT 'vip 8',
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `level` smallint(6) DEFAULT NULL COMMENT '级别',
  `goodsid` varchar(100) NOT NULL COMMENT '物品',
  `consume_wayid` int(11) NOT NULL COMMENT '获得方式',
  `consume_wayclassid` int(11) NOT NULL COMMENT '获得方式所属分类(任务，拍卖行)',
  `total_cnt` bigint(20) NOT NULL COMMENT '人次',
  `unique_cnt` int(11) NOT NULL COMMENT '人数',
  `gold_sum` bigint(20) NOT NULL COMMENT '获取金币总数量',
  `poundage` bigint(20) NOT NULL COMMENT '手续费总数量',
  `goodsnum` bigint(20) NOT NULL COMMENT '物品总数量',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`dimension`, `clientid`, `level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='金币vip消耗日统计表' '''
class GoldVipConsumeDay(Merge):
    TABLE_NAME = "gold_vipconsume_day"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _gold_vipconsume_day_sql


_blue_diamond_get_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `vip_level` smallint(6) DEFAULT NULL,
  `bdiamond_sum` int(11) NOT NULL DEFAULT 0 COMMENT '数量',
  `bdiamond_total` int(11) NOT NULL DEFAULT 0 COMMENT '目前总数量',
  `bdiamond_wayid` int(11) NOT NULL COMMENT '获得方式ID',
  `bdiamond_wayclassid` int(11) NOT NULL COMMENT '获得方式分类ID',
  `get_time` int(11) NOT NULL COMMENT '获得时间戳',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  `extend_2` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `get_time` (`get_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='蓝钻获得表' '''
class BluediamondGet(ClientSplitModel):
    TABLE_NAME = "blue_diamond_get"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _blue_diamond_get_sql


_diamond_get_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `dimension` smallint(6) DEFAULT NULL COMMENT 'dau1,新用户2,首付费3,流水4,历史付费7',
  `type` varchar(32) NOT NULL COMMENT '钻石类型(bind，unbind)',
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `get_wayid` int(11) NOT NULL COMMENT '获得方式ID',
  `get_wayclassid` int(11) NOT NULL COMMENT '获得方式分类ID',
  `total_cnt` int(11) NOT NULL COMMENT '人次',
  `unique_cnt` int(11) NOT NULL COMMENT '人数',
  `diamond_sum` int(11) NOT NULL DEFAULT 0 COMMENT '获取数量',
  `diamond_total` bigint(20) NOT NULL DEFAULT 0 COMMENT '目前总数量',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`dimension`, `clientid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='钻石获得统计表' '''
class DiamondGetDay(Merge):
    TABLE_NAME = "diamond_get_day"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _diamond_get_day_sql


_yellow_diamond_get_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `vip_level` smallint(6) DEFAULT NULL,
  `diamond_sum` int(11) NOT NULL DEFAULT 0 COMMENT '数量',
  `diamond_total` int(11) NOT NULL DEFAULT 0 COMMENT '目前总数量',
  `poundage` int(11) NOT NULL COMMENT  '购买物品的手续费',
  `diamond_wayid` int(11) NOT NULL COMMENT '获得方式ID',
  `diamond_wayclassid` int(11) NOT NULL COMMENT '获得方式分类ID',
  `get_time` int(11) NOT NULL COMMENT '获得时间戳',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  `extend_2` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `get_time` (`get_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='金钻非充值获得表' '''
class YellowdiamondGet(ClientSplitModel):
    TABLE_NAME = "yellow_diamond_get"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _yellow_diamond_get_sql

_consume_d_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT 0,
  `vip_level` smallint(6) DEFAULT NULL,
  `consume_time` int(11) NOT NULL COMMENT '消耗时间戳',
  `consume_sum_b` int(11) NOT NULL DEFAULT 0 COMMENT '消耗绑定钻石数',
  `own_after_b` int(11) NOT NULL DEFAULT 0 COMMENT '消耗后剩余绑定钻石数',
  `consume_sum_fb` int(11) NOT NULL DEFAULT 0 COMMENT '消耗非绑定钻石数(包括手续费)',
  `own_after_fb` int(11) NOT NULL DEFAULT 0 COMMENT '消耗后剩余非绑定钻石数',
  `poundage` int(11) NOT NULL COMMENT  '购买物品的手续费',
  `goodsid` varchar(200) DEFAULT NULL COMMENT '物品ID',
  `goodsprice` decimal(10,2) NOT NULL DEFAULT 0 COMMENT '物品单价',
  `goodsnum` int(11) NOT NULL DEFAULT 0 COMMENT '物品数量',
  `consume_wayid` int(11) NOT NULL COMMENT '消耗的具体方式ID',
  `consume_wayclassid` int(11) NOT NULL COMMENT '消耗的方式',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  `extend_2` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `consume_time` (`consume_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='钻石消耗' '''
class ConsumeD(ClientSplitModel):
    TABLE_NAME = "consume_d"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _consume_d_sql


_diamond_consume_day_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `dimension` smallint(6) DEFAULT NULL COMMENT 'dau为1,新增为2,新付费为3,所有付费为5,消耗金币为6',
  `goodsid` varchar(200) DEFAULT NULL COMMENT '物品ID',
  `consume_wayid` int(11) NOT NULL COMMENT '消耗方式ID',
  `consume_wayclassid` int(11) NOT NULL COMMENT '消耗的分类方式',
  `consume_sum_b` int(11) NOT NULL DEFAULT 0 COMMENT '消耗绑定钻石数',
  `consume_sum_fb` int(11) NOT NULL DEFAULT 0 COMMENT '消耗非绑定钻石数(包括手续费)',
  `own_after_b` int(11) NOT NULL DEFAULT 0 COMMENT '消耗后剩余绑定钻石数',
  `own_after_fb` int(11) NOT NULL DEFAULT 0 COMMENT '消耗后剩余非绑定钻石数',
  `consume_cnt` int(11) NOT NULL COMMENT '消耗次数',
  `consume_per` int(11) NOT NULL COMMENT '消耗人数',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`dimension`,`clientid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='钻石消耗统计表' '''
class DiamondConsumeDay(Merge):
    TABLE_NAME = "diamond_consume_day"
    CREATE_SQL = _diamond_consume_day_sql


_other_get_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `vip_level` smallint(6) DEFAULT NULL,
  `get_time` int(11) NOT NULL COMMENT '时间戳',
  `other_sum` int(11) DEFAULT NULL COMMENT '本次获得金币数量',
  `other_total` int(11) DEFAULT NULL COMMENT '目前金币总数量',
  `poundage` int(11) NOT NULL COMMENT '手续费(拍卖行购买物品需交手续费)',
  `get_wayid` int(11) NOT NULL COMMENT '获得方式',
  `get_wayclassid` int(11) NOT NULL COMMENT '获得方式所属分类(任务，拍卖行)',
  `currency_type` varchar(200) DEFAULT NULL COMMENT '类别',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `get_time` (`get_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Other 货币产出表' '''
class OtherGet(ClientSplitModel):
    TABLE_NAME = "other_get"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _other_get_sql


_other_get_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `dimension` smallint(6) DEFAULT NULL COMMENT 'dau1,新用户2,首付费3,流水4,历史付费7',
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `get_wayid` int(11) NOT NULL COMMENT '获得方式',
  `get_wayclassid` int(11) NOT NULL COMMENT '获得方式所属分类(任务，拍卖行)',
  `total_cnt` bigint(20) NOT NULL COMMENT '人次',
  `unique_cnt` int(11) NOT NULL COMMENT '人数',
  `other_sum` bigint(20) NOT NULL COMMENT '获取金币总数量',
  `poundage` bigint(20) NOT NULL COMMENT '手续费总数量',
  `currency_type` varchar(200) DEFAULT NULL COMMENT '类别',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`dimension`, `clientid`, `currency_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Other 货币产出日统计表' '''
class OtherGetDay(Merge):
    TABLE_NAME = "other_get_day"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _other_get_day_sql


_other_consume_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT NULL,
  `vip_level` smallint(6) DEFAULT NULL,
  `consume_time` int(11) NOT NULL COMMENT '时间戳',
  `other_sum` int(11) DEFAULT NULL COMMENT '本次消耗金币数量',
  `other_total` int(11) DEFAULT NULL COMMENT '剩余金币总数量',
  `poundage` int(11) NOT NULL COMMENT '手续费(拍卖行购买物品需交手续费)',
  `consume_wayid` int(11) NOT NULL COMMENT '消耗方式(装备升级)',
  `consume_wayclassid` int(11) NOT NULL COMMENT '消耗的用处',
  `goodsid` varchar(100) NOT NULL COMMENT '物品ID',
  `goodsprice` decimal(10,2) DEFAULT NULL COMMENT '物品单价',
  `goodsnum` int(11) DEFAULT NULL COMMENT '物品数量',
  `currency_type` varchar(200) DEFAULT NULL COMMENT '类别',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `consume_time` (`consume_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Other 货币消耗表' '''
class OtherConsume(ClientSplitModel):
    TABLE_NAME = "other_consume"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _other_consume_sql


_other_consume_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `dimension` smallint(6) DEFAULT NULL COMMENT 'dau1,新用户2,首付费3,流水4,历史付费7',
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `goodsid` varchar(100) NOT NULL COMMENT '物品',
  `consume_wayid` int(11) NOT NULL COMMENT '获得方式',
  `consume_wayclassid` int(11) NOT NULL COMMENT '获得方式所属分类(任务，拍卖行)',
  `total_cnt` bigint(20) NOT NULL COMMENT '人次',
  `unique_cnt` int(11) NOT NULL COMMENT '人数',
  `other_sum` bigint(20) NOT NULL COMMENT '获取金币总数量',
  `poundage` bigint(20) NOT NULL COMMENT '手续费总数量',
  `goodsnum` bigint(20) NOT NULL COMMENT '物品总数量',
  `currency_type` varchar(200) DEFAULT NULL COMMENT '类别',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`dimension`, `clientid`, `currency_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Other 货币消耗日统计表' '''
class OtherConsumeDay(Merge):
    TABLE_NAME = "other_consume_day"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _other_consume_day_sql


_crystal_get_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT 0,
  `vip_level` smallint(6) DEFAULT NULL,
  `crystal_sum` int(11) NOT NULL DEFAULT 0 COMMENT '数量',
  `crystal_total` int(11) NOT NULL DEFAULT 0 COMMENT '目前总数量',
  `poundage` int(11) NOT NULL COMMENT  '购买物品的手续费',
  `get_wayid` int(11) NOT NULL COMMENT '获得方式ID',
  `get_wayclassid` int(11) NOT NULL COMMENT '获得方式的分类',
  `get_time` int(11) NOT NULL COMMENT '获得时间戳',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  `extend_2` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `get_time` (`get_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='水晶获得表' '''
class CrystalGet(ClientSplitModel):
    TABLE_NAME = "crystal_get"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _crystal_get_sql

_crystal_consume_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT 0,
  `vip_level` smallint(6) DEFAULT NULL,
  `crystal_sum` int(11) NOT NULL DEFAULT 0 COMMENT '数量(包括手续费)',
  `crystal_total` int(11) NOT NULL DEFAULT 0 COMMENT '目前总数量',
  `poundage` int(11) NOT NULL COMMENT  '购买物品的手续费',
  `consume_wayid` int(11) NOT NULL COMMENT '消耗具体方式ID',
  `consume_wayclassid` int(11) NOT NULL COMMENT '消耗方式ID',
  `goodsid` varchar(200) DEFAULT NULL COMMENT '物品ID',
  `goodsprice` decimal(10,2) NOT NULL DEFAULT 0 COMMENT '物品单价',
  `goodsnum` int(11) NOT NULL DEFAULT 0 COMMENT '物品数量',
  `consume_time` int(11) NOT NULL COMMENT '消耗时间戳',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  `extend_2` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `consume_time` (`consume_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='水晶消耗表' '''
class CrystalConsume(ClientSplitModel):
    TABLE_NAME = "crystal_consume"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _crystal_consume_sql

_magic_crystal_get_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT 0,
  `vip_level` smallint(6) DEFAULT NULL,
  `magic_crystal_sum` int(11) NOT NULL DEFAULT 0 COMMENT '数量',
  `magic_crystal_total` int(11) NOT NULL DEFAULT 0 COMMENT '目前总数量',
  `poundage` int(11) NOT NULL COMMENT  '购买物品的手续费',
  `get_wayid` int(11) NOT NULL COMMENT '获得方式ID',
  `get_wayclassid` int(11) NOT NULL COMMENT '获得方式的分类',
  `get_time` int(11) NOT NULL COMMENT '获得时间戳',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  `extend_2` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `get_time` (`get_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='魔晶获得表' '''
class MagicCrystalGet(ClientSplitModel):
    TABLE_NAME = "magic_crystal_get"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _magic_crystal_get_sql


_magic_crystal_consume_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `IP` varchar(64) DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `level` smallint(6) DEFAULT 0,
  `vip_level` smallint(6) DEFAULT NULL,
  `magic_crystal_sum` int(11) NOT NULL DEFAULT 0 COMMENT '数量(包括手续费)',
  `magic_crystal_total` int(11) NOT NULL DEFAULT 0 COMMENT '目前总数量',
  `poundage` int(11) NOT NULL COMMENT  '购买物品的手续费',
  `consume_wayid` int(11) NOT NULL COMMENT '消耗具体方式ID',
  `consume_wayclassid` int(11) NOT NULL COMMENT '消耗方式ID',
  `goodsid` varchar(200) DEFAULT NULL COMMENT '物品ID',
  `goodsprice` decimal(10,2) NOT NULL DEFAULT 0 COMMENT '物品单价',
  `goodsnum` int(11) NOT NULL DEFAULT 0 COMMENT '物品数量',
  `consume_time` int(11) NOT NULL COMMENT '消耗时间戳',
  `extend_1` varchar(200) DEFAULT NULL COMMENT '预留',
  `extend_2` varchar(200) DEFAULT NULL COMMENT '预留',
  PRIMARY KEY (`id`),
  KEY `consume_time` (`consume_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='魔晶消耗表' '''
class MagicCrystalConsume(ClientSplitModel):
    TABLE_NAME = "magic_crystal_consume"
    OLDBI_TABLE = TABLE_NAME
    NEWBI_TABLE = TABLE_NAME
    CREATE_SQL = _magic_crystal_consume_sql

# 统计数据库

_register_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `login_cnt` int(11) DEFAULT NULL COMMENT '累计用户数',
  `first_login_cnt` int(11) DEFAULT NULL COMMENT '新登用户数',
  `mac_cnt` int(11) DEFAULT NULL COMMENT '总设备数',
  `install_cnt` int(11) DEFAULT NULL COMMENT '新增设备数',
  `dau` int(11) DEFAULT NULL COMMENT '日活跃用户数',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`snid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='帐号日统计报表' '''
class RegisterDay(Merge):
    TABLE_NAME = "user_register_day"
    CREATE_SQL = _register_day_sql


_login_online_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `dimention` SMALLINT(6) NOT NULL COMMENT '等级->1,vip等级->2',
  `level` SMALLINT(6) NOT NULL DEFAULT 0 COMMENT '等级',
  `user` int(11) NOT NULL DEFAULT 0 COMMENT '总在线人数',
  `user_online` bigint(20) NOT NULL DEFAULT 0 COMMENT '总在线时长',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`, `gameid`,`clientid`, `dimention`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='登录时长' '''
class LoginOnlineDay(Merge):
    TABLE_NAME = "login_online_day"
    CREATE_SQL = _login_online_day_sql


_user_rolepay_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` INT(11) NOT NULL COMMENT '区服ID',
  `user_rolepay_cnt` int(11) DEFAULT NULL COMMENT '衮服新增',
  `free_cnt` int(11) DEFAULT NULL COMMENT '衮服免费用户新增',
  `pay_cnt` int(11) DEFAULT NULL COMMENT '衮服付费用户新增',
  `free_pay_cnt` int(11) DEFAULT NULL COMMENT '衮服免费用户付费人数',
  `free_pay_amount` DECIMAL(10,2) DEFAULT NULL COMMENT '衮服免费用户付费金额',
  `pay_continue_cnt` int(11) DEFAULT NULL COMMENT '衮服付费用户付费人数',
  `pay_continue_amount` DECIMAL(10,2) DEFAULT NULL COMMENT '衮服付费用户付费金额',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`clientid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='衮服充值日统计表' '''
class UserRolePay(Merge):
    TABLE_NAME = "user_rolepay_day"
    CREATE_SQL = _user_rolepay_day_sql

# _pay_day_sql = '''\
#   `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
#   `ds` date DEFAULT NULL,
#   `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
#   `clientid` int(11) NOT NULL COMMENT '区服ID',
#   `snid` int(11) NOT NULL COMMENT '平台ID',
#   `user_pay_cnt` int(11) DEFAULT NULL COMMENT '充值用户数',
#   `pay_cnt` decimal(10,2) DEFAULT NULL COMMENT '充值次数',
#   `first_pay_cnt` int(11) DEFAULT NULL COMMENT '首充总人数',
#   `amount` decimal(10,2) DEFAULT NULL COMMENT '金额',
#   `currency` varchar(10) DEFAULT NULL COMMENT '货币类型',
#   `val` int(11) DEFAULT NULL COMMENT '购买的游戏币(元宝 、钻石)数量',
#   `role_register_cnt` int(11) DEFAULT NULL COMMENT '角色创建人数',
#   `role_active_cnt` int(11) DEFAULT NULL COMMENT '角色活跃人数',
#   PRIMARY KEY (`id`),
#   UNIQUE KEY `dx1` (`ds`,`gameid`,`clientid`,`snid`)
# ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='用户充值日统计报表' '''
_pay_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `user_pay_cnt` int(11) DEFAULT NULL COMMENT '充值用户数',
  `pay_cnt` int(11) DEFAULT NULL COMMENT '充值次数',
  `first_pay_cnt` int(11) DEFAULT NULL COMMENT '首充总人数',
  `amount` decimal(10,2) DEFAULT NULL COMMENT '金额',
  `first_amount` decimal(10,2) DEFAULT NULL COMMENT '首充总金额',
  `max_amount` decimal(10,2) DEFAULT NULL COMMENT '最高总金额',
  `currency` varchar(10) DEFAULT NULL COMMENT '货币类型',
  `val` int(11) DEFAULT NULL COMMENT '购买的游戏币(元宝 、钻石)数量',
  `new_register_cnt` INT(11) NOT NULL DEFAULT 0 COMMENT '新注册用户数',
  `new_register_amount` INT(11) NOT NULL DEFAULT 0 COMMENT '新注册用户付费金额',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`clientid`,`snid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='用户充值日统计报表' '''
class PayDay(Merge):
    TABLE_NAME = "user_pay_day"
    CREATE_SQL = _pay_day_sql


_role_new_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `first_cnt` int(11) DEFAULT NULL COMMENT '新增用户',
  `roll_cnt` int(11) DEFAULT NULL COMMENT '滚服新增用户',
  `dau` int(11) DEFAULT NULL COMMENT '日活跃用户数',
  `missing` int(11) DEFAULT NULL COMMENT '流失用户数',
  `hispay` int(11) DEFAULT NULL COMMENT '历史付费用户数',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`clientid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='角色日统计报表' '''
class RoleNewDay(Merge):
    TABLE_NAME = "role_new_day"
    CREATE_SQL = _role_new_day_sql


_online_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `max_online_cnt` int(11) DEFAULT NULL COMMENT '最高在线人数',
  `avg_online_cnt` int(11) DEFAULT NULL COMMENT '平均在线人数',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='在线日统计报表' '''
class OnlineDay(Merge):
    TABLE_NAME = "online_day"
    CREATE_SQL = _online_day_sql


_role_level_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `level` smallint(6) DEFAULT NULL,
  `role_cnt` int(11) DEFAULT NULL COMMENT '当天角色人数',
  `role_cnt_d2` int(11) DEFAULT NULL COMMENT '次日角色人数',
  `role_cnt_d3` int(11) DEFAULT NULL COMMENT '三日角色人数',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`clientid`,`snid`,`level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='新角色等级分布表' '''
class RoleLevelDay(Merge):
    TABLE_NAME = "newrole_level"
    CREATE_SQL = _role_level_sql


_resident_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `dimension` smallint(6) DEFAULT NULL COMMENT 'dau1,新用户2,首付费3,流失4',
  `level` smallint(6) DEFAULT NULL,
  `user_cnt` int(11) DEFAULT NULL COMMENT '用户驻留数',
  `percent` int(11) DEFAULT NULL COMMENT '占比,17.7->177',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`clientid`,`dimension`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='等级驻留统计' '''
class ResidentDay(Merge):
    TABLE_NAME = "resident_day"
    CREATE_SQL = _resident_day_sql


_vip_resident_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `vip_level` smallint(6) DEFAULT NULL,
  `vip_cnt` int(11) DEFAULT NULL COMMENT 'vip驻留数',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`clientid`,`snid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='vip等级驻留统计表' '''
class VipResidentDay(Merge):
    TABLE_NAME = "vip_level_resident"
    CREATE_SQL = _vip_resident_sql


_register_pay_resident_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `dimension` smallint(6) DEFAULT NULL COMMENT '用户留存1,支付率2',
  `resident_cnt` int(11) DEFAULT NULL COMMENT '新增数',
  `resident_d2` int(11) DEFAULT NULL COMMENT '次日存留',
  `resident_d3` int(11) DEFAULT NULL COMMENT '3日存留',
  `resident_d4` int(11) DEFAULT NULL COMMENT '4日存留',
  `resident_d5` int(11) DEFAULT NULL COMMENT '5日存留',
  `resident_d6` int(11) DEFAULT NULL COMMENT '6日存留',
  `resident_d7` int(11) DEFAULT NULL COMMENT '7日存留',
  `resident_d8` int(11) DEFAULT NULL COMMENT '8日存留',
  `resident_d9` int(11) DEFAULT NULL COMMENT '9日存留',
  `resident_d10` int(11) DEFAULT NULL COMMENT '10日存留',
  `resident_d11` int(11) DEFAULT NULL COMMENT '11日存留',
  `resident_d12` int(11) DEFAULT NULL COMMENT '12日存留',
  `resident_d13` int(11) DEFAULT NULL COMMENT '13日存留',
  `resident_d14` int(11) DEFAULT NULL COMMENT '14日存留',
  `resident_d15` int(11) DEFAULT NULL COMMENT '15日存留',
  `resident_d16` int(11) DEFAULT NULL COMMENT '16日存留',
  `resident_d17` int(11) DEFAULT NULL COMMENT '17日存留',
  `resident_d18` int(11) DEFAULT NULL COMMENT '18日存留',
  `resident_d19` int(11) DEFAULT NULL COMMENT '19日存留',
  `resident_d20` int(11) DEFAULT NULL COMMENT '20日存留',
  `resident_d21` int(11) DEFAULT NULL COMMENT '21日存留',
  `resident_d22` int(11) DEFAULT NULL COMMENT '22日存留',
  `resident_d23` int(11) DEFAULT NULL COMMENT '23日存留',
  `resident_d24` int(11) DEFAULT NULL COMMENT '24日存留',
  `resident_d25` int(11) DEFAULT NULL COMMENT '25日存留',
  `resident_d26` int(11) DEFAULT NULL COMMENT '26日存留',
  `resident_d27` int(11) DEFAULT NULL COMMENT '27日存留',
  `resident_d28` int(11) DEFAULT NULL COMMENT '28日存留',
  `resident_d29` int(11) DEFAULT NULL COMMENT '29日存留',
  `resident_d30` int(11) DEFAULT NULL COMMENT '30日存留',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ds` (`ds`,`gameid`,`snid`,`dimension`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='注册帐号存留' '''
class RegisterPayResidentDay(Merge):
    TABLE_NAME = "register_pay_resident"
    CREATE_SQL = _register_pay_resident_sql


_register_pay_resident_clientid_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `dimension` smallint(6) DEFAULT NULL COMMENT '用户留存1,支付率2',
  `resident_cnt` int(11) DEFAULT NULL COMMENT '新增数',
  `resident_d2` int(11) DEFAULT NULL COMMENT '次日存留',
  `resident_d3` int(11) DEFAULT NULL COMMENT '3日存留',
  `resident_d4` int(11) DEFAULT NULL COMMENT '4日存留',
  `resident_d5` int(11) DEFAULT NULL COMMENT '5日存留',
  `resident_d6` int(11) DEFAULT NULL COMMENT '6日存留',
  `resident_d7` int(11) DEFAULT NULL COMMENT '7日存留',
  `resident_d8` int(11) DEFAULT NULL COMMENT '8日存留',
  `resident_d9` int(11) DEFAULT NULL COMMENT '9日存留',
  `resident_d10` int(11) DEFAULT NULL COMMENT '10日存留',
  `resident_d11` int(11) DEFAULT NULL COMMENT '11日存留',
  `resident_d12` int(11) DEFAULT NULL COMMENT '12日存留',
  `resident_d13` int(11) DEFAULT NULL COMMENT '13日存留',
  `resident_d14` int(11) DEFAULT NULL COMMENT '14日存留',
  `resident_d15` int(11) DEFAULT NULL COMMENT '15日存留',
  `resident_d16` int(11) DEFAULT NULL COMMENT '16日存留',
  `resident_d17` int(11) DEFAULT NULL COMMENT '17日存留',
  `resident_d18` int(11) DEFAULT NULL COMMENT '18日存留',
  `resident_d19` int(11) DEFAULT NULL COMMENT '19日存留',
  `resident_d20` int(11) DEFAULT NULL COMMENT '20日存留',
  `resident_d21` int(11) DEFAULT NULL COMMENT '21日存留',
  `resident_d22` int(11) DEFAULT NULL COMMENT '22日存留',
  `resident_d23` int(11) DEFAULT NULL COMMENT '23日存留',
  `resident_d24` int(11) DEFAULT NULL COMMENT '24日存留',
  `resident_d25` int(11) DEFAULT NULL COMMENT '25日存留',
  `resident_d26` int(11) DEFAULT NULL COMMENT '26日存留',
  `resident_d27` int(11) DEFAULT NULL COMMENT '27日存留',
  `resident_d28` int(11) DEFAULT NULL COMMENT '28日存留',
  `resident_d29` int(11) DEFAULT NULL COMMENT '29日存留',
  `resident_d30` int(11) DEFAULT NULL COMMENT '30日存留',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ds` (`ds`,`gameid`,`clientid`,`dimension`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='注册帐号存留' '''
class RegisterPayResidentClientidDay(Merge):
    TABLE_NAME = "register_pay_resident_clientid"
    CREATE_SQL = _register_pay_resident_clientid_sql


_ltv_resident_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `dimension` smallint(6) DEFAULT NULL COMMENT '用户留存1,支付率2',
  `resident_cnt` int(11) DEFAULT NULL COMMENT '新增数',
  `resident_d1` int(11) DEFAULT NULL COMMENT '首日付费额存留',
  `resident_d2` int(11) DEFAULT NULL COMMENT '次日存留',
  `resident_d3` int(11) DEFAULT NULL COMMENT '3日存留',
  `resident_d4` int(11) DEFAULT NULL COMMENT '4日存留',
  `resident_d5` int(11) DEFAULT NULL COMMENT '5日存留',
  `resident_d6` int(11) DEFAULT NULL COMMENT '6日存留',
  `resident_d7` int(11) DEFAULT NULL COMMENT '7日存留',
  `resident_d8` int(11) DEFAULT NULL COMMENT '8日存留',
  `resident_d9` int(11) DEFAULT NULL COMMENT '9日存留',
  `resident_d10` int(11) DEFAULT NULL COMMENT '10日存留',
  `resident_d11` int(11) DEFAULT NULL COMMENT '11日存留',
  `resident_d12` int(11) DEFAULT NULL COMMENT '12日存留',
  `resident_d13` int(11) DEFAULT NULL COMMENT '13日存留',
  `resident_d14` int(11) DEFAULT NULL COMMENT '14日存留',
  `resident_d15` int(11) DEFAULT NULL COMMENT '15日存留',
  `resident_d16` int(11) DEFAULT NULL COMMENT '16日存留',
  `resident_d17` int(11) DEFAULT NULL COMMENT '17日存留',
  `resident_d18` int(11) DEFAULT NULL COMMENT '18日存留',
  `resident_d19` int(11) DEFAULT NULL COMMENT '19日存留',
  `resident_d20` int(11) DEFAULT NULL COMMENT '20日存留',
  `resident_d21` int(11) DEFAULT NULL COMMENT '21日存留',
  `resident_d22` int(11) DEFAULT NULL COMMENT '22日存留',
  `resident_d23` int(11) DEFAULT NULL COMMENT '23日存留',
  `resident_d24` int(11) DEFAULT NULL COMMENT '24日存留',
  `resident_d25` int(11) DEFAULT NULL COMMENT '25日存留',
  `resident_d26` int(11) DEFAULT NULL COMMENT '26日存留',
  `resident_d27` int(11) DEFAULT NULL COMMENT '27日存留',
  `resident_d28` int(11) DEFAULT NULL COMMENT '28日存留',
  `resident_d29` int(11) DEFAULT NULL COMMENT '29日存留',
  `resident_d30` int(11) DEFAULT NULL COMMENT '30日存留',
  `resident_d31` int(11) DEFAULT NULL COMMENT '31日存留',
  `resident_d32` int(11) DEFAULT NULL COMMENT '32日存留',
  `resident_d33` int(11) DEFAULT NULL COMMENT '33日存留',
  `resident_d34` int(11) DEFAULT NULL COMMENT '34日存留',
  `resident_d35` int(11) DEFAULT NULL COMMENT '35日存留',
  `resident_d36` int(11) DEFAULT NULL COMMENT '36日存留',
  `resident_d37` int(11) DEFAULT NULL COMMENT '37日存留',
  `resident_d38` int(11) DEFAULT NULL COMMENT '38日存留',
  `resident_d39` int(11) DEFAULT NULL COMMENT '39日存留',
  `resident_d40` int(11) DEFAULT NULL COMMENT '40日存留',
  `resident_d41` int(11) DEFAULT NULL COMMENT '41日存留',
  `resident_d42` int(11) DEFAULT NULL COMMENT '42日存留',
  `resident_d43` int(11) DEFAULT NULL COMMENT '43日存留',
  `resident_d44` int(11) DEFAULT NULL COMMENT '44日存留',
  `resident_d45` int(11) DEFAULT NULL COMMENT '45日存留',
  `resident_d46` int(11) DEFAULT NULL COMMENT '46日存留',
  `resident_d47` int(11) DEFAULT NULL COMMENT '47日存留',
  `resident_d48` int(11) DEFAULT NULL COMMENT '48日存留',
  `resident_d49` int(11) DEFAULT NULL COMMENT '49日存留',
  `resident_d50` int(11) DEFAULT NULL COMMENT '50日存留',
  `resident_d51` int(11) DEFAULT NULL COMMENT '51日存留',
  `resident_d52` int(11) DEFAULT NULL COMMENT '52日存留',
  `resident_d53` int(11) DEFAULT NULL COMMENT '53日存留',
  `resident_d54` int(11) DEFAULT NULL COMMENT '54日存留',
  `resident_d55` int(11) DEFAULT NULL COMMENT '55日存留',
  `resident_d56` int(11) DEFAULT NULL COMMENT '56日存留',
  `resident_d57` int(11) DEFAULT NULL COMMENT '57日存留',
  `resident_d58` int(11) DEFAULT NULL COMMENT '58日存留',
  `resident_d59` int(11) DEFAULT NULL COMMENT '59日存留',
  `resident_d60` int(11) DEFAULT NULL COMMENT '60日存留',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ds` (`ds`,`gameid`,`snid`,`dimension`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='LTV存留' '''
class LTVResidentDay(Merge):
    TABLE_NAME = "ltv_resident"
    CREATE_SQL = _ltv_resident_sql

_consume_day_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `dimension` smallint(6) DEFAULT NULL COMMENT 'dau为1,新增为2,新付费为3,所有付费为5,消耗金币为6',
  `goodsid` varchar(64) NOT NULL COMMENT '物品ID',
  `consume_cnt` int(11) NOT NULL COMMENT '消耗次数',
  `consume_per` int(11) NOT NULL COMMENT '消耗人数',
  `consume_sum` int(11) NOT NULL COMMENT '消耗金额',
  `consume_goodsnum` int(11) NOT NULL DEFAULT 0 COMMENT '消耗金额',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`clientid`,`dimension`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='消耗统计表' '''
class ConsumeDay(Merge):
    TABLE_NAME = "consume_day"
    CREATE_SQL = _consume_day_sql

_vipconsume_day_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `dimension` smallint(6) DEFAULT NULL COMMENT 'vip等级为2',
  `level` smallint(6) DEFAULT 0 COMMENT '等级',
  `goodsid` varchar(64) NOT NULL COMMENT '物品ID',
  `consume_cnt` int(11) NOT NULL COMMENT '消耗次数',
  `consume_per` int(11) NOT NULL COMMENT '消耗人数',
  `consume_sum` int(11) NOT NULL COMMENT '消耗金额',
  `consume_goodsnum` int(11) NOT NULL DEFAULT 0 COMMENT '消耗金额',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`clientid`,`dimension`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='消耗统计表' '''
class VipConsumeDay(Merge):
    TABLE_NAME = "vipconsume_day"
    CREATE_SQL = _vipconsume_day_sql

_props_consume_day_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `dimension` smallint(6) DEFAULT NULL COMMENT 'dau为1,新增为2,新付费为3,所有付费为5,消耗金币为6',
  `consume_wayid` int(11) NOT NULL COMMENT '消耗方式ID',
  `consume_wayclassid` int(11) NOT NULL COMMENT '消耗的分类方式',
  `propsid` varchar(64) NOT NULL COMMENT '物品ID',
  `consume_cnt` int(11) NOT NULL COMMENT '消耗次数',
  `consume_per` int(11) NOT NULL COMMENT '消耗人数',
  `consume_sum` int(11) NOT NULL default 0 COMMENT '消耗总数量',
  `after_sum` int(11) NOT NULL default 0 COMMENT '剩余总数量',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`dimension`,`clientid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='道具消耗统计表' '''
class PropsConsumeDay(Merge):
    TABLE_NAME = "props_consume_day"
    CREATE_SQL = _props_consume_day_sql

_mission_day_sql = '''\
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ds` date DEFAULT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `dimension` smallint(6) DEFAULT NULL COMMENT 'dau1,新用户2,首付费3,流水4,历史付费7',
  `mission_type` smallint(6) DEFAULT NULL COMMENT '关卡1，任务2，副本3',
  `mission_level` varchar(50) DEFAULT "" COMMENT '级别',
  `event_id` varchar(32) DEFAULT NULL COMMENT '（任务、关卡、副本）ID',
  `event_name` varchar(64) DEFAULT NULL COMMENT '（任务、关卡、副本）名称',
  `all_user` int(11) DEFAULT NULL COMMENT '参与人数',
  `pass_user` int(11) DEFAULT NULL COMMENT '通过人数',
  `all_cnt` int(11) DEFAULT NULL COMMENT '参与次数',
  `pass_cnt` int(11) DEFAULT NULL COMMENT '通过次数',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`clientid`,`dimension`,`mission_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='关卡统计' '''
class MissionDay(Merge):
    TABLE_NAME = "mission_day"
    CREATE_SQL = _mission_day_sql


_pay_month_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) DEFAULT NULL COMMENT '区服ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `pay_cnt` int(11) NOT NULL COMMENT '充值次数',
  `user_pay_cnt` int(11) NOT NULL COMMENT '充值人数',
  `amount` int(11) NOT NULL COMMENT '消耗金额',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`clientid`,`snid`),
  KEY `ds` (`ds`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='月充值统计表' '''
class PayMonth(Merge):
    TABLE_NAME = "pay_month"
    CREATE_SQL = _pay_month_sql


_login_month_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `user_pay_cnt` int(11) NOT NULL COMMENT '活跃人数',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`snid`),
  KEY `ds` (`ds`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='月账号活跃表' '''
class ActiveMonth(Merge):
    TABLE_NAME = "user_login_month"
    CREATE_SQL = _login_month_sql


_pay_rich_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `rank` smallint(6) NOT NULL COMMENT '排名',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `amount` int(11) NOT NULL COMMENT '消耗金额',
  `val` int(11) DEFAULT NULL COMMENT '购买的游戏币(元宝 、钻石)数量',
  `consume_sum` int(11) DEFAULT NULL COMMENT '消耗虚拟货币数量',
  `own_after` int(11) DEFAULT NULL COMMENT '剩余货币数量',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`snid`, `rank`),
  KEY `ds` (`ds`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='富豪排行榜' '''
class PayRich(Merge):
    TABLE_NAME = "pay_rich"
    CREATE_SQL = _pay_rich_sql


_pay_rich_multi_roleid_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `rank` smallint(6) NOT NULL COMMENT '排名',
  `openid` varchar(100) NOT NULL COMMENT '用户平台账号',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `roleid` varchar(64) NOT NULL COMMENT '用户区服唯一账号',
  `amount` int(11) NOT NULL COMMENT '消耗金额',
  `val` int(11) DEFAULT NULL COMMENT '购买的游戏币(元宝 、钻石)数量',
  `consume_sum` int(11) DEFAULT NULL COMMENT '消耗虚拟货币数量',
  `own_after` int(11) DEFAULT NULL COMMENT '剩余货币数量',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`snid`, `rank`),
  KEY `ds` (`ds`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='多角色富豪排行榜' '''
class PayRichMultiRoleid(Merge):
    TABLE_NAME = "pay_rich_multi_roleid"
    CREATE_SQL = _pay_rich_multi_roleid_sql


_vip_pay_struct_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `dimention` smallint(6) NOT NULL COMMENT '日维度->1,月维度->2',
  `vip_level` smallint(6) NOT NULL COMMENT '等级',
  `user_cnt` int(11) NOT NULL COMMENT '用户数',
  `amount` int(11) NOT NULL COMMENT '消耗金额',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`snid`,`dimention`, `vip_level`),
  KEY `ds` (`ds`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='vip付费构成' '''
class VipPayStruct(Merge):
    TABLE_NAME = "vip_pay_struct"
    CREATE_SQL = _vip_pay_struct_sql


_payment_gear_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `dimention` smallint(6) NOT NULL COMMENT '日维度->1,月维度->2',
  `pay_gear` int(11) NOT NULL COMMENT '充值档位',
  `pay_cnt` int(11) NOT NULL COMMENT '充值人数',
  `pay_timecnt` int(11) NOT NULL COMMENT '充值次数',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`snid`,`dimention`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='充值档位分布' '''
class PaymentGear(Merge):
    TABLE_NAME = "payment_gear"
    CREATE_SQL = _payment_gear_sql


_month_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `first_login_cnt` int(11) DEFAULT NULL COMMENT '新登用户数',
  `install_cnt` int(11) DEFAULT NULL COMMENT '新增设备数',
  `mau` int(11) NOT NULL COMMENT '活跃人数',
  `first_pay_cnt` int(11) DEFAULT NULL COMMENT '首充总人数',
  `user_pay_cnt` int(11) DEFAULT NULL COMMENT '充值用户数',
  `first_amount` decimal(10,2) DEFAULT NULL COMMENT '新付费金额',
  `amount` decimal(20,2) DEFAULT NULL COMMENT '消耗金额',
  `val` bigint(20) DEFAULT NULL COMMENT '购买的游戏币(元宝 、钻石)数量',
  `gold_sum` bigint(20) NOT NULL COMMENT '消耗金币',
  `resident_install` INT(11) NOT NULL DEFAULT 0 COMMENT '新增用户留存数',
  `resident_noinstall` INT(11) NOT NULL DEFAULT 0 COMMENT '非新增用户留存数',
  `new_register_cnt` INT(11) NOT NULL DEFAULT 0 COMMENT '新注册用户数',
  `new_register_amount` INT(11) NOT NULL DEFAULT 0 COMMENT '新注册用户付费金额',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`snid`),
  KEY `ds` (`ds`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='月统计表' '''
class Month(Merge):
    TABLE_NAME = "month"
    CREATE_SQL = _month_sql


_month_consume_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `consume_sum` bigint(20) NOT NULL COMMENT '消耗的钻石数量',
  `own` bigint(20) NOT NULL DEFAULT 0 COMMENT '月末钻石存量',
  `own_after_sum` bigint(20) NOT NULL DEFAULT 0 COMMENT '僵尸用户钻石存量',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='月消耗统计表' '''
class MonthConsume(Merge):
    TABLE_NAME = "month_consume"
    CREATE_SQL = _month_consume_sql


_realtime_online_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `ti` time NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `user` int(11) NOT NULL COMMENT '在线人数',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`clientid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='实时在线用户数' '''
class RealtimeOnline(Merge):
    TABLE_NAME = "realtime_online"
    CREATE_SQL = _realtime_online_sql


_realtime_register_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `ti` time NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `clientid` int(11) NOT NULL COMMENT '区服ID',
  `register` int(11) NOT NULL COMMENT '注册人数',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`clientid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='实时在线用户数' '''
class RealtimeRegister(Merge):
    TABLE_NAME = "realtime_register"
    CREATE_SQL = _realtime_register_sql


realtime_income_newer_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `ti` time NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `newer` int(11) NOT NULL COMMENT '新用户',
  `income` int(11) NOT NULL COMMENT '累计收入',
  `payer` int(11) NOT NULL COMMENT '付费用户数',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`snid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='实时在线收入和新用户' '''
class RealtimeIncomeNewer(Merge):
    TABLE_NAME = "realtime_income_newer"
    CREATE_SQL = realtime_income_newer_sql


realtime_redident_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `ti` time NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `snid` int(11) NOT NULL COMMENT '平台ID',
  `newer` int(11) NOT NULL COMMENT '新用户',
  `dau` int(11) NOT NULL COMMENT '当日活跃',
  `resident` int(11) NOT NULL COMMENT '次日存留',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`,`gameid`,`snid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='实时在线次日存留' '''
class RealtimeResident(Merge):
    TABLE_NAME = "realtime_resident"
    CREATE_SQL = realtime_redident_sql


log_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `type` smallint(6) NOT NULL COMMENT '类型',
  `msg` varchar(1024) NOT NULL COMMENT '内容',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`, `gameid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='日志' '''
class Log(Merge):
    TABLE_NAME = "log"
    CREATE_SQL = log_sql
    #
    FILTER_TYPE = 1   # 补数据情况


logger_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `type` smallint(6) NOT NULL COMMENT '类型1代表分析脚本代码',
  `msg` varchar(1024) NOT NULL COMMENT '内容内容,gameid,状态码,错误信息',
  PRIMARY KEY (`id`),
  KEY `dx1` (`ds`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='日志记录' '''
class Logger(Merge):
    TABLE_NAME = "logger"
    CREATE_SQL = logger_sql

kv_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `key` varchar(32) NOT NULL,
  `value` varchar(10240) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='配置' '''
class Kv(Merge):
    TABLE_NAME = "kv"
    CREATE_SQL = kv_sql


ip_geo_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `category` smallint(6) NOT NULL DEFAULT 0 COMMENT '所属分类',
  `country` varchar(32) DEFAULT NULL COMMENT '国家',
  `provice` varchar(32) DEFAULT NULL COMMENT '省份',
  `city` varchar(32) DEFAULT NULL COMMENT '城市',
  `count` int(11) NOT NULL COMMENT '数量',
  `total_count` int(11) NOT NULL COMMENT '总量',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='IP地址地理信息统计' '''
class IPGeo(Merge):
    TABLE_NAME = "ip_geo"
    CREATE_SQL = ip_geo_sql


ad_role_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `unionid` varchar(50) NOT NULL COMMENT '联盟ID',
  `new` bigint(20) NOT NULL DEFAULT 0 COMMENT '用户数量',
  `register_d1` bigint(20) NOT NULL DEFAULT 0 COMMENT 'd1',
  `register_d2` bigint(20) NOT NULL DEFAULT 0 COMMENT 'd2, 当天新注册用户在未来两天新建角色数量',
  `register_d3` bigint(20) NOT NULL DEFAULT 0 COMMENT 'd3',
  `register_d4` bigint(20) NOT NULL DEFAULT 0 COMMENT 'd4',
  `register_d5` bigint(20) NOT NULL DEFAULT 0 COMMENT 'd5',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`unionid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='广告新角色统计' '''
class AdRole(Merge):
    TABLE_NAME = "ad_role"
    CREATE_SQL = ad_role_sql


ad_user_register_sql = '''\
  `IP` bigint(20) NOT NULL DEFAULT '-1' COMMENT '注册IP',
  `gameid` int(11) NOT NULL COMMENT '游戏id',
  `union_id` varchar(50) DEFAULT NULL COMMENT '联盟ID',
  `openid` varchar(100) NOT NULL COMMENT '用户ID',
  `user_name` varchar(250) NOT NULL COMMENT '用户名',
  `email` varchar(50) DEFAULT NULL COMMENT '邮箱',
  `mobile` varchar(20) DEFAULT NULL COMMENT '手机号',
  `reg_time` int(10) unsigned NOT NULL DEFAULT '0' COMMENT '注册时间',
  `type` tinyint(1) NOT NULL COMMENT '是否新老注册,1为新用户,2为老用户',
  UNIQUE KEY `openid` (`openid`,`gameid`,`type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='用户详细信息表' '''
class AdUserRegister(Model):
    TABLE_NAME = "ad_user_register"
    CREATE_SQL = ad_user_register_sql


ad_payment_sql = '''\
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ds` date NOT NULL,
  `gameid` varchar(32) NOT NULL COMMENT '游戏ID',
  `unionid` varchar(50) NOT NULL COMMENT '联盟ID',
  `num` bigint(20) NOT NULL DEFAULT 0 COMMENT '付费人数',
  `cnt` bigint(20) NOT NULL DEFAULT 0 COMMENT '付费次数',
  `amount` bigint(20) NOT NULL DEFAULT 0 COMMENT '付费金额',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dx1` (`ds`,`gameid`,`unionid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='广告付费统计' '''
class AdPayMent(Merge):
    TABLE_NAME = "ad_payment"
    CREATE_SQL = ad_payment_sql


def test():
    print(DDL.create("user", "2100007", True))


def test_check_field():
    print(check_fields(_login_month_sql))


def test_insert():
    ActiveMonth.insert({"ds": "2015-08-25", "gameid": "2100007", "snid": 11, "user_pay_cnt": 100})

if __name__ == "__main__":
    test_insert()
