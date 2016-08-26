# coding=utf8

import os
import sys
import time
import random
import logging
import datetime
import traceback
import ConfigParser
from logging import handlers
from functools import wraps, partial

import torndb


"""
login全服所有
game, log库单服

在线  ：game库player表：lastoptm int default 0 comment '上次玩家和服务器交互的时间',

充值：login库 order表

登陆：log库 login表

创角：game库helix_player表

消耗：log库 log_jewel表（钻石日志表，记录钻石的增、减）

mission：log_pve(typeid类别，等同于mission_level、stageid关卡id， 都是成功的）     log库 log_raidboss表 打boss

物品获得搜“获得”,log库log_get_card表（物品id用card_key）和log_get_equip表(装备id用equip_key）

物品消耗搜“use_” log库log_use_medal表和log_use_equip表

金币获得与消耗：log_gold表

其他币种：公会币log_guild_coin表、PVP徽章log_badge表

快照从game库的helix_player表取
"""


GAME_LEVEL = "game"      # game级别
SERVER_LEVEL = "server"  # server级别

log = logging.getLogger("bi")
env = None


def log_init(filename):
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    rotate = handlers.RotatingFileHandler(filename, maxBytes=10 * 1024 * 1024, backupCount=0)
    rotate.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s')
    console.setFormatter(fmt)
    rotate.setFormatter(fmt)
    log.addHandler(console)
    log.addHandler(rotate)
    log.setLevel(logging.DEBUG)


def env_init():
    # 获取工作目录
    filename = sys.argv[0].rsplit(os.path.sep, 1)
    if len(filename) > 1:   # 非游戏目录
        cwd = filename[0]
    else:
        cwd = os.path.realpath(os.getcwd())

    # 获取配置文件
    cf = ConfigParser.ConfigParser()
    config_path = os.path.join(cwd, "config.ini")
    cf.read(config_path)

    # 初始化日志
    filename = cf.get(SERVER_LEVEL, "log")
    log_init(filename)

    env = dict(cwd=cwd, cf=cf, config_path=config_path)

    return env

env = env_init()


def log_level(level):
    """记录日志"""
    assert level in ("debug", "info", "warn", "error")

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            use = time.time() - start
            msg = "sql [{0}s]: {1}".format(use, args if len(args)>1 else args[0])
            if kwargs:
                msg = "{0}, parameters: {1}".format(msg, kwargs)
            getattr(log, level)(msg)
            return result
        return wrapper
    return decorator


class Connection(object):
    CONNECTIONS = {}

    @classmethod
    def create(cls, level=SERVER_LEVEL):
        """远程服还是本地服 """
        if level not in cls.CONNECTIONS:
            get = partial(env["cf"].get, level)
            log.warning("mysql connection init, level: %s", level)
            conn = torndb.Connection(get("host"), get("db_default"), user=get("user"), password=get("password"), time_zone="+8:00")
            cls.CONNECTIONS[level] = cls(conn)
        return cls.CONNECTIONS[level]

    def __init__(self, conn):
        self.conn = conn

    def __getattr__(self, name):
        func = getattr(self.conn, name)
        return log_level("info")(func)


class Util(object):
    @classmethod
    def timestamp_datetime(cls, timestamp, strf=True):
        if strf:
            return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        else:
            return datetime.datetime.fromtimestamp(timestamp)

    @classmethod
    def datetime_timestamp(cls, date_time):
        return int(time.mktime(date_time.timetuple()))


class Extract(object):
    def __init__(self, start):
        self.start = start
        self.datetime = datetime.datetime.fromtimestamp(start)
        self.file = None
        self.set_up()

    def set_up(self):
        self.env = self.get_env()
        self.dst = env["cf"].get(SERVER_LEVEL, "data_dir")
        self.filename = self.get_filename()

        log.info("now time:%s", self.start)
        self.reopen()
        self.init_unit()

    def reopen(self):
        self.close()
        path = os.path.join(self.dst, self.filename)
        log.info("open file:%s", path)
        self.file = open(path, "w")

    def write(self, line):
        try:
            self.file.write(line)
        except Exception as e:
            log.error("write error:%s\n%s", str(e), traceback.format_exc())
            self.reopen()

    def close(self):
        if self.file is not None:
            try:
                self.file.close()
            except Exception as e:
                log.error("close log file:%s error:%s", self.filename, str(e))

    def get_env(self):
        get = partial(env["cf"].get, SERVER_LEVEL)
        return {
            "clientid": get("clientid"),
            "gameid": get("gameid"),
            "start": self.start,
            "datetime": self.datetime,
            "date": str(self.datetime.date()),
            "time": str(self.datetime.time().replace(microsecond=0)),
            "currency": get("currency")
        }

    def get_filename(self):
        """获取文件名"""
        date = self.datetime.strftime("%Y-%m-%d-%H-%M-%S")
        clientid = int(self.env["clientid"])
        rand = "".join([str(random.randrange(0, 9)) for i in range(6)])
        return "{date}-{clientid:05d}_{rand}.log.tmp".format(**locals())

    def rename_filename(self):
        new_name = self.filename.rstrip(".tmp")
        old_path = os.path.join(self.dst, self.filename)
        new_path = os.path.join(self.dst, new_name)
        log.info("file rename to %s", new_path)
        os.rename(old_path, new_path)

    def init_unit(self):
        self.units = [
            Online(self),
            Login(self),
            Payment(self),
            Mission(self),
            RoleNew(self),
            Consume(self),
        ]

    def run(self):
        for unit in self.units:
            log.info("unit [%s] start", unit.__class__)
            try:
                unit.set_up()
                unit.extract()
            except Exception as e:
                unit.failed(e)
                err = "{0}\n{1}".format(str(e), traceback.format_exc())
                log.error(err)
                log.info("unit [%s] end failed", unit.__class__)
            else:
                unit.success()
                log.info("unit [%s] end success", unit.__class__)

        self.close()
        self.rename_filename()
        log.info("######\n")


class ConsumeExtract(Extract):

    def init_unit(self):
        self.units = [
            Props(self),
            Gold(self),
            Other(self)
        ]


class Unit(object):
    def __init__(self, owner):
        self.owner = owner
        self.env = self.owner.env
        self.cf = env["cf"]

    def set_up(self):
        pass

    def __getattr__(self, name):
        return getattr(self.owner, name)

    def extract(self):
        pass

    def failed(self, e):
        """extract异常时调用"""
        pass

    def get_db(self, db_name, level=SERVER_LEVEL):
        return self.config_get(db_name, level)

    def config_set(self, key, value, level=SERVER_LEVEL):
        self.cf.set(level, key, value)

    def config_get(self, key, level=SERVER_LEVEL):
        return self.cf.get(level, key)

    def config_save(self):
        self.cf.write(open(env["config_path"], "w"))

    def get_snid(self, snid):
        return self.config_get("default_snid") if snid == 0 else snid

    def success(self):
        """extract成功时调用"""
        pass

    def fill(self, row, delimiter='#'):
        """
        BI_online|gameid#|snid{1}
        BI_online|gameid{{{gameid}}}|snid{1}
        """
        fields = []
        for key in row.split('|'):
            start = key.find(delimiter)
            if start != -1:
                key = "{0}{{{{{{{0}}}}}}}{1}".format(key[:start], key[start + 1:])
            fields.append(key)

        return "|".join(fields)


class Online(Unit):
    """在线人数"""
    def extract(self):
        common = dict(self.env)
        common["db_game"] = self.get_db("db_game")
        common["start"] -= 120
        common["online_timestamp"] = common["start"]
        online_dt = Util.timestamp_datetime(float(common["online_timestamp"]), strf=False)
        common["online_date"] = str(online_dt.date())
        common["online_time"] = str(online_dt.time())

        sql = "select count(*) as users from {db_game}.helix_player where lastoptm>={start}".format(**common)
        common["users"] = Connection.create(SERVER_LEVEL).get(sql)["users"]

        # row = "BI_online|gameid{{{gameid}}}|clientid{{{clientid}}}|online_timestamp{{{online_timestamp}}}|users{{{users}}}|online_date{{{online_date}}}|online_time{{{online_time}}}\n"
        row = self.fill("BI_online|gameid#|clientid#|online_timestamp#|users#|online_date#|online_time#\n")

        self.write(row.format(**common))


class Login(Unit):
    """用户登录和角色登录"""
    def extract(self):
        common = dict(self.env)
        common["db_game"] = self.get_db("db_game")
        common["db_log"] = self.get_db("db_log")
        login_start = self.config_get("login_start")
        common["login_start"] = Util.timestamp_datetime(float(login_start))
        common["start_dt"] = Util.timestamp_datetime(common["start"])

        log.info("config.ini, login_start = %s(%s)" % (login_start, common["login_start"]))
        sql = "select log_login.*, helix_player.lv as level from {db_log}.log_login inner join {db_game}.helix_player on log_login.playerid=helix_player.playerid and login_tm>='{login_start}' and login_tm<'{start_dt}'".format(**common)
        logins = Connection.create(SERVER_LEVEL).iter(sql)

        for login in logins:
            common["IP"] = login["login_ip"]
            common["snid"] = self.get_snid(login["subid"])
            common["openid"] = login["uid"]
            common["device"] = ""
            common["OS"] = ""
            common["MAC"] = ""
            common["login_timestamp"] = Util.datetime_timestamp(login["login_tm"])
            common["login_date"] = str(login["login_tm"].date())
            common["login_time"] = str(login["login_tm"].time())

            common["type"] = "1"
            common["roleid"] = login["playerid"]
            common["level"] = login["level"]
            common["online_time"] = "0"
            common["rolelogin_timestamp"] = common["login_timestamp"]
            common["rolelogin_date"] = common["login_date"]
            common["rolelogin_time"] = common["login_time"]

            row_login = self.fill("BI_login|IP#|gameid#|snid#|openid#|device#|OS#|MAC#|login_timestamp#|login_date#|login_time#\n")
            row_role_login = self.fill("BI_role_login|IP#|gameid#|clientid#|snid#|type#|openid#|roleid#|level#|online_time#|rolelogin_timestamp#|rolelogin_date#|rolelogin_time#\n")

            self.write(row_login.format(**common))
            self.write(row_role_login.format(**common))

    def success(self):
        login_start = self.env["start"]
        self.config_set("login_start", login_start)
        self.config_save()

        login_start_dt = Util.timestamp_datetime(float(login_start))
        log.info("Login success, update login_start to %s(%s)" % (login_start, login_start_dt))


class Payment(Unit):
    """充值表"""
    def set_up(self):
        self.start = self.env["start"] - 300

    def extract(self):
        common = dict(self.env)
        common["db_login"] = self.get_db("db_login", GAME_LEVEL)
        common["db_game"] = self.get_db("db_game")
        common["clientid"] = common["clientid"]
        common["currency"] = common["currency"]
        payment_start = self.config_get("payment_start")
        common["payment_start"] = Util.timestamp_datetime(float(payment_start))
        common["start_dt"] = Util.timestamp_datetime(self.start)
        common["IP"] = ""

        sql_order = "select platformid, gsid, subid, uid, playerid, money, jewel, sdk_orderid, createtm from {db_login}.helix_order where createtm >='{payment_start}' and createtm<'{start_dt}' and gsid={clientid} and order_result=1 and feed_result=1".format(**common)
        values_order = Connection.create(GAME_LEVEL).query(sql_order)
        if not values_order:
            return

        log.info("config.ini, payment_start = %s(%s)" % (payment_start, common["payment_start"]))

        playerids = ','.join([str(low["playerid"]) for low in values_order])
        common["playerids"] = playerids
        sql_player = "select playerid, lv, vip from {db_game}.helix_player where playerid in ({playerids})".format(**common)
        values_player = Connection.create(SERVER_LEVEL).query(sql_player)
        players = {}
        for player in values_player:
            players[player["playerid"]] = {"vip": player["vip"], "level": player["lv"]}

        for order in values_order:
            common["openid"] = order["uid"]
            common["snid"] = self.get_snid(order["subid"])
            common["roleid"] = order["playerid"]
            common["amount"] = order["money"]
            common["val"] = order["jewel"]
            common["transactionid"] = order["sdk_orderid"]
            common["payment_timestamp"] = Util.datetime_timestamp(order["createtm"])
            common["payment_date"] = order["createtm"].date()
            common["payment_time"] = order["createtm"].time()

            player = players.get(order["playerid"])
            common["level"] = 0 if player is None else player["level"]
            common["vip_level"] = 0 if player is None else player["vip"]
            row_payment = self.fill("BI_payment|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|amount#|currency#|val#|transactionid#|payment_timestamp#|payment_date#|payment_time#\n")
            self.write(row_payment.format(**common))

    def success(self):
        payment_start = self.start
        self.config_set("payment_start", payment_start)
        self.config_save()
        payment_start_dt = Util.timestamp_datetime(float(payment_start))
        log.info("payment success, update payment_start to %s(%s)" % (payment_start, payment_start_dt))


class RoleNew(Unit):
    """角色建立"""
    def extract(self):
        common = dict(self.env)
        common["db_game"] = self.get_db("db_game")
        common["reg_start"] = self.config_get("register_start")
        reg_start_dt = Util.timestamp_datetime(float(common["reg_start"]))

        log.info("config.ini, register_start = %s(%s)" % (common["reg_start"], reg_start_dt))
        sql = "select * from {db_game}.helix_player where createtm>='{reg_start}' and createtm<'{start}'".format(**common)
        role_news = Connection.create(SERVER_LEVEL).iter(sql)

        for role_new in role_news:
            common["IP"] = ""
            common["snid"] = self.get_snid(role_new["subid"])
            common["openid"] = role_new["uid"]
            common["roleid"] = role_new["playerid"]
            common["rolename"] = role_new["playername"].encode("utf-8").replace("\r", "").replace("\n", "").replace("|", "").replace("{", "").replace("}", "")
            common["school"] = role_new["myguildid"]
            common["role_timestamp"] = role_new["createtm"]
            createtm_dt = Util.timestamp_datetime(float(role_new["createtm"]), strf=False)
            common["role_date"] = str(createtm_dt.date())
            common["role_time"] = str(createtm_dt.time())

            row_role_new = self.fill("BI_role_new|IP#|gameid#|clientid#|snid#|openid#|roleid#|rolename#|school#|role_timestamp#|role_date#|role_time#\n")
            self.write(row_role_new.format(**common))

    def success(self):
        reg_start = self.env["start"]
        self.config_set("register_start", reg_start)
        self.config_save()

        reg_start_dt = Util.timestamp_datetime(float(reg_start))
        log.info("RoleNew success, update register_start to %s(%s)" % (reg_start, reg_start_dt))


class Consume(Unit):
    """消耗"""
    def extract(self):
        common = dict(self.env)
        common["db_game"] = self.get_db("db_game")
        common["db_log"] = self.get_db("db_log")
        consume_start = self.config_get("consume_start")
        common["consume_start"] = Util.timestamp_datetime(float(consume_start))
        common["start_dt"] = Util.timestamp_datetime(common["start"])

        log.info("config.ini, consume_start = %s(%s)" % (consume_start, common["consume_start"]))
        sql = "select log_jewel.*, helix_player.lv as level, helix_player.vip as vip_level from {db_log}.log_jewel inner join {db_game}.helix_player on log_jewel.playerid=helix_player.playerid and num<0 and log_tm>='{consume_start}' and log_tm<'{start_dt}'".format(**common)
        consumes = Connection.create(SERVER_LEVEL).iter(sql)

        for consume in consumes:
            common["IP"] = ""
            common["snid"] = self.get_snid(consume["subid"])
            common["openid"] = consume["uid"]
            common["roleid"] = consume["playerid"]
            common["level"] = consume["level"]
            common["vip_level"] = consume["vip_level"]
            common["consume_timestamp"] = Util.datetime_timestamp(consume["log_tm"])
            common["consume_sum"] = abs(consume["num"])
            common["own_after"] = consume["new_num"]
            common["goodsid"] = consume["fromid"]
            common["goodsprice"] = common["consume_sum"]
            common["goodsnum"] = 1
            common["consume_date"] = str(consume["log_tm"].date())
            common["consume_time"] = str(consume["log_tm"].time())

            row_consume = self.fill("BI_consume|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|consume_timestamp#|consume_sum#|own_after#|goodsid#|goodsprice#|goodsnum#|consume_date#|consume_time#\n")
            self.write(row_consume.format(**common))

    def success(self):
        consume_start = self.env["start"]
        self.config_set("consume_start", consume_start)
        self.config_save()

        consume_start_dt = Util.timestamp_datetime(float(consume_start))
        log.info("Consume success, update login_start to %s(%s)" % (consume_start, consume_start_dt))


class Mission(Unit):
    """关卡表"""

    def extract(self):
        common = dict(self.env)
        common["db_log"] = self.get_db("db_log")
        common["db_game"] = self.get_db("db_game")
        common["clientid"] = common["clientid"]
        mission_start = self.config_get("mission_start")
        common["mission_start"] = Util.timestamp_datetime(float(mission_start))
        common["start_datetime"] = Util.timestamp_datetime(common["start"])
        common["IP"] = ""
        common["event_name"] = ""
        common["mission_type"] = 1

        log.info("config.ini, mission_start = %s(%s)" % (mission_start, common["mission_start"]))
        self.log_raidboss(common)
        self.log_pve(common)

    def log_raidboss(self, common):
        sql_raidboss = "select uid1 as uid, start_tm, stage_key, start_tm, result from {db_log}.log_raidboss where start_tm >= '{mission_start}' and start_tm < '{start_datetime}' and uid1 is not null and  uid1 != 0 union all select uid2 as uid, start_tm, stage_key, start_tm, result from {db_log}.log_raidboss where start_tm >= '{mission_start}' and start_tm < '{start_datetime}' and uid2 is not null and  uid2 != 0 union all select uid3 as uid, start_tm, stage_key, start_tm, result from {db_log}.log_raidboss where start_tm >= '{mission_start}' and start_tm < '{start_datetime}' and uid3 is not null and  uid3 != 0 union all select uid4 as uid, start_tm, stage_key, start_tm, result from {db_log}.log_raidboss where start_tm >= '{mission_start}' and start_tm < '{start_datetime}' and uid4 is not null and  uid4 != 0".format(**common)
        values_raidboss = Connection.create(SERVER_LEVEL).query(sql_raidboss)
        if not values_raidboss:
            return
        uids_raidboss = ','.join('"%s"' % low["uid"] for low in values_raidboss)
        common["uids_raidboss"] = uids_raidboss

        sql_boss_player = "select uid, playerid, subid, lv, vip from {db_game}.helix_player where  uid in ({uids_raidboss})".format(**common)
        values_boss_player = Connection.create(SERVER_LEVEL).query(sql_boss_player)

        player_raidboss = {}
        for player in values_boss_player:
            player_raidboss[player["uid"]] = {"playerid": player["playerid"], "vip": player["vip"], "lv": player["lv"], "subid": player["subid"]}

        for boss in values_raidboss:
            common["openid"] = boss["uid"]
            common["mission_timestamp"] = Util.datetime_timestamp(boss["start_tm"])
            common["event_date"] = boss["start_tm"].date()
            common["event_time"] = boss["start_tm"].time()
            common["mission_level"] = "普通"
            common["event_ID"] = boss["stage_key"]
            common["event_OK"] = 2 if boss["result"] == 1 else 1
            common["mission_type"] = 2

            player = player_raidboss.get(boss["uid"])

            common["level"] = 0 if player is None else player["lv"]
            common["vip_level"] = 0 if player is None else player["vip"]
            common["roleid"] = 0 if player is None else player["playerid"]
            common["snid"] = 0 if player is None else player["subid"]
            common["snid"] = self.get_snid(common["snid"])

            row_mission = self.fill("BI_mission|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|mission_timestamp#|event_date#|event_time#|mission_type#|mission_level#|event_name#|event_ID#|event_OK#\n")
            self.write(row_mission.format(**common))

    def log_pve(self, common):
        sql_pve = "select subid, uid, playerid, pve_tm, typeid, stageid, pve_tm, mapid from {db_log}.log_pve where pve_tm >='{mission_start}' and pve_tm < '{start_datetime}'".format(**common)
        values_pve = Connection.create(SERVER_LEVEL).query(sql_pve)
        if not values_pve:
            return
        uids_pve = ','.join([str(low["playerid"]) for low in values_pve])
        common["uids_pve"] = uids_pve
        sql_player = "select uid, playerid, subid, lv, vip from {db_game}.helix_player where playerid in ({uids_pve})".format(**common)
        values_player = Connection.create(SERVER_LEVEL).query(sql_player)
        player_pve = {}
        for player in values_player:
            player_pve[player["uid"]] = {"vip": player["vip"], "lv": player["lv"], "subid": player["subid"], "playerid": player["playerid"]}

        for pve in values_pve:
            common["openid"] = pve["uid"]
            common["mission_timestamp"] = Util.datetime_timestamp(pve["pve_tm"])
            common["event_date"] = pve["pve_tm"].date()
            common["event_time"] = pve["pve_tm"].time()
            common["mission_level"] = pve["typeid"]
            common["event_ID"] = "%s:%s:%s" % (pve["mapid"], pve["typeid"], pve["stageid"])
            common["event_OK"] = 2
            common["mission_type"] = 1

            player = player_pve.get(pve["uid"])

            common["level"] = 0 if player is None else player["lv"]
            common["vip_level"] = 0 if player is None else player["vip"]
            common["roleid"] = 0 if player is None else player["playerid"]
            common["snid"] = 0 if player is None else player["subid"]
            common["snid"] = self.get_snid(common["snid"])

            row_mission = self.fill("BI_mission|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|mission_timestamp#|event_date#|event_time#|mission_type#|mission_level#|event_name#|event_ID#|event_OK#\n")
            self.write(row_mission.format(**common))

    def success(self):
        mission_start = self.env["start"]
        self.config_set("mission_start", mission_start)
        self.config_save()
        mission_start_datetime = Util.timestamp_datetime(float(mission_start))
        log.info("mission success, update mission_start to %s(%s)" % (mission_start, mission_start_datetime))


class Gold(Unit):
    """金币获得/消耗表"""
    def extract(self):
        common = dict(self.env)
        common["db_log"] = self.get_db("db_log")
        common["db_game"] = self.get_db("db_game")
        common["clientid"] = common["clientid"]
        gold_start = self.config_get("gold_start")
        common["gold_start"] = Util.timestamp_datetime(float(gold_start))
        common["start_datetime"] = Util.timestamp_datetime(common["start"])
        common["IP"] = ""
        common["poundage"] = 0
        common["extend_1"] = ""
        common["extend_2"] = ""

        sql_gold="select log_gold.*, helix_player.lv, helix_player.vip, log_tm from {db_log}.log_gold inner join {db_game}.helix_player on log_gold.playerid=helix_player.playerid and log_tm>='{gold_start}' and log_tm<'{start_datetime}'".format(**common)
        values_gold = Connection.create(SERVER_LEVEL).iter(sql_gold)
        for gold in values_gold:
            self.glod_get(common, gold)
            self.glod_consume(common, gold)

    def glod_get(self, common, gold):
        if gold["num"] >=0:
            common["openid"] = gold["uid"]
            common["get_timestamp"] = Util.datetime_timestamp(gold["log_tm"])
            common["get_date"] = gold["log_tm"].date()
            common["get_time"] = gold["log_tm"].time()
            common["level"] = gold["lv"]
            common["vip_level"] = gold["vip"]
            common["roleid"] = gold["playerid"]
            common["snid"] = self.get_snid(gold["subid"])
            common["get_wayid"] = gold["fromid"]
            common["get_wayclassid"] = gold["fromid"]
            common["gold_sum"] = gold["num"]
            common["gold_total"] = gold["new_num"]

            row_goldget = self.fill("BI_gold_get|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|gold_sum#|gold_total#|poundage#|get_wayid#|get_wayclassid#|get_timestamp#|get_date#|get_time#|extend_1#|extend_2#\n")
            self.write(row_goldget.format(**common))

    def glod_consume(self, common, gold):
        if gold["num"] < 0:
            common["openid"] = gold["uid"]
            common["consume_timestamp"] = Util.datetime_timestamp(gold["log_tm"])
            common["consume_date"] = gold["log_tm"].date()
            common["consume_time"] = gold["log_tm"].time()
            common["level"] = gold["lv"]
            common["vip_level"] = gold["vip"]
            common["roleid"] = gold["playerid"]
            common["snid"] = self.get_snid(gold["subid"])
            common["consume_wayid"] = gold["fromid"]
            common["consume_wayclassid"] = gold["fromid"]
            common["gold_sum"] = gold["num"]
            common["gold_total"] = gold["new_num"]
            common["goodsid"] = gold["fromid"]
            common["goodsprice"] = gold["num"]
            common["goodsnum"] = 1

            row_goldconsume = self.fill("BI_gold_consume|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|gold_sum#|gold_total#|poundage#|consume_wayid#|consume_wayclassid#|goodsid#|goodsprice#|goodsnum#|consume_timestamp#|consume_date#|consume_time#|extend_1#|extend_2#\n")
            self.write(row_goldconsume.format(**common))

    def success(self):
        gold_start = self.env["start"]
        self.config_set("gold_start", gold_start)
        self.config_save()
        gold_start_datetime = Util.timestamp_datetime(float(gold_start))
        log.info("gold success, update gold_start to %s(%s)" % (gold_start, gold_start_datetime))


class Other(Unit):
    """其他货币获得/消耗表"""
    def extract(self):
        common = dict(self.env)
        common["db_log"] = self.get_db("db_log")
        common["db_game"] = self.get_db("db_game")
        common["clientid"] = common["clientid"]
        other_start = self.config_get("other_start")
        common["other_start"] = Util.timestamp_datetime(float(other_start))
        common["start_datetime"] = Util.timestamp_datetime(common["start"])
        common["IP"] = ""
        common["poundage"] = 0
        common["extend_1"] = ""

        self.other_badge(common)
        self.other_guild(common)

    def other_badge(self, common):
        """pvp徽章 消耗与 获得"""
        sql_badge="select log_badge.*, helix_player.lv, helix_player.vip from {db_log}.log_badge inner join {db_game}.helix_player on log_badge.playerid=helix_player.playerid and log_tm>='{other_start}' and log_tm<'{start_datetime}'".format(**common)
        values_badge = Connection.create(SERVER_LEVEL).iter(sql_badge)
        for badge in values_badge:
            if badge["num"] >= 0:
                common["openid"] = badge["uid"]
                common["get_timestamp"] = Util.datetime_timestamp(badge["log_tm"])
                common["get_date"] = badge["log_tm"].date()
                common["get_time"] = badge["log_tm"].time()
                common["level"] = badge["lv"]
                common["vip_level"] = badge["vip"]
                common["roleid"] = badge["playerid"]
                common["snid"] = self.get_snid(badge["subid"])
                common["get_wayid"] = badge["fromid"]
                common["get_wayclassid"] = badge["fromid"]
                common["other_sum"] = badge["num"]
                common["other_total"] = badge["new_num"]
                common["currency_type"] = "pvp徽章"

                row_badge_get = self.fill("BI_other_get|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|other_sum#|other_total#|poundage#|get_wayid#|get_wayclassid#|get_timestamp#|get_date#|get_time#|currency_type#|extend_1#\n")
                self.write(row_badge_get.format(**common))

            elif badge["num"] < 0:
                common["openid"] = badge["uid"]
                common["consume_timestamp"] = Util.datetime_timestamp(badge["log_tm"])
                common["consume_date"] = badge["log_tm"].date()
                common["consume_time"] = badge["log_tm"].time()
                common["level"] = badge["lv"]
                common["vip_level"] = badge["vip"]
                common["roleid"] = badge["playerid"]
                common["snid"] = self.get_snid(badge["subid"])
                common["consume_wayid"] = badge["fromid"]
                common["consume_wayclassid"] = badge["fromid"]
                common["other_sum"] = badge["num"]
                common["other_total"] = badge["new_num"]
                common["currency_type"] = "pvp徽章"
                common["goodsid"] = badge["fromid"]
                common["goodsprice"] = badge["num"]
                common["goodsnum"] = 1

                row_badge_consume = self.fill("BI_other_consume|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|other_sum#|other_total#|poundage#|consume_wayid#|consume_wayclassid#|goodsid#|goodsprice#|goodsnum#|consume_timestamp#|consume_date#|consume_time#|currency_type#|extend_1#\n")
                self.write(row_badge_consume.format(**common))

    def other_guild(self, common):
        """公会币 消耗与 获得"""
        sql_badge="select log_guild_coin.*, helix_player.lv, helix_player.vip from {db_log}.log_guild_coin inner join {db_game}.helix_player on log_guild_coin.playerid=helix_player.playerid and log_tm>='{other_start}' and log_tm<'{start_datetime}'".format(**common)
        values_badge = Connection.create(SERVER_LEVEL).iter(sql_badge)
        for badge in values_badge:
            if badge["num"] >=0:
                common["openid"] = badge["uid"]
                common["get_timestamp"] = Util.datetime_timestamp(badge["log_tm"])
                common["get_date"] = badge["log_tm"].date()
                common["get_time"] = badge["log_tm"].time()
                common["level"] = badge["lv"]
                common["vip_level"] = badge["vip"]
                common["roleid"] = badge["playerid"]
                common["snid"] = self.get_snid(badge["subid"])
                common["get_wayid"] = badge["fromid"]
                common["get_wayclassid"] = badge["guildid"]
                common["other_sum"] = badge["num"]
                common["other_total"] = badge["new_num"]
                common["currency_type"] = "公会币"

                row_guild_get = self.fill("BI_other_get|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|other_sum#|other_total#|poundage#|get_wayid#|get_wayclassid#|get_timestamp#|get_date#|get_time#|currency_type#|extend_1#\n")
                self.write(row_guild_get.format(**common))

            elif badge["num"] < 0:
                common["openid"] = badge["uid"]
                common["consume_timestamp"] = Util.datetime_timestamp(badge["log_tm"])
                common["consume_date"] = badge["log_tm"].date()
                common["consume_time"] = badge["log_tm"].time()
                common["level"] = badge["lv"]
                common["vip_level"] = badge["vip"]
                common["roleid"] = badge["playerid"]
                common["snid"] = self.get_snid(badge["subid"])
                common["consume_wayid"] = badge["fromid"]
                common["consume_wayclassid"] = badge["guildid"]
                common["other_sum"] = badge["num"]
                common["other_total"] = badge["new_num"]
                common["currency_type"] = "公会币"
                common["goodsid"] = badge["guildid"]
                common["goodsprice"] = badge["num"]
                common["goodsnum"] = 1

                row_guild_consume = self.fill("BI_other_consume|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|other_sum#|other_total#|poundage#|consume_wayid#|consume_wayclassid#|goodsid#|goodsprice#|goodsnum#|consume_timestamp#|consume_date#|consume_time#|currency_type#|extend_1#\n")
                self.write(row_guild_consume.format(**common))

    def success(self):
        other_start = self.env["start"]
        self.config_set("other_start", other_start)
        self.config_save()
        other_start_datetime = Util.timestamp_datetime(float(other_start))
        log.info("other success, update other_start to %s(%s)" % (other_start, other_start_datetime))


class Props(Unit):
    """道具获得与消耗"""
    def extract(self):
        common = dict(self.env)
        common["db_game"] = self.get_db("db_game")
        common["db_log"] = self.get_db("db_log")
        props_start = self.config_get("props_start")
        common["props_start"] = Util.timestamp_datetime(float(props_start))
        common["start_dt"] = Util.timestamp_datetime(common["start"])

        log.info("config.ini, props_start = %s(%s)" % (props_start, common["props_start"]))
        self.props_get(common)
        self.props_consume(common)

    def props_get(self, common):
        sqls = {
            "card": "select a.playerid, a.uid, a.subid, a.card_key as propsid, a.num, a.fromid as get_wayid, a.get_tm, b.lv as level, b.vip as vip_level from {db_log}.log_get_card as a inner join {db_game}.helix_player as b on a.playerid=b.playerid and a.num>0 and get_tm>='{props_start}' and get_tm<'{start_dt}'".format(**common),
            "equip": "select a.playerid, a.uid, a.subid, a.equip_key as propsid, a.num, a.fromid as get_wayid, a.get_tm, b.lv as level, b.vip as vip_level from {db_log}.log_get_equip as a inner join {db_game}.helix_player as b on a.playerid=b.playerid and a.num>0 and get_tm>='{props_start}' and get_tm<'{start_dt}'".format(**common),
            "medal": "select a.playerid, a.uid, a.subid, a.medal_key as propsid, a.fromid, a.from_mapid as get_wayid, a.from_stageid, a.num, a.new_num, a.log_tm as get_tm, b.lv as level, b.vip as vip_level from {db_log}.log_get_medal as a inner join {db_game}.helix_player as b on a.playerid=b.playerid and a.num>0 and log_tm>='{props_start}' and log_tm<'{start_dt}'".format(**common),
        }
        for k, sql in sqls.iteritems():
            log.info("props_get, %s" % k)
            props_gets = Connection.create(SERVER_LEVEL).iter(sql)
            for props_get in props_gets:
                common["IP"] = ""
                common["snid"] = self.get_snid(props_get["subid"])
                common["openid"] = props_get["uid"]
                common["roleid"] = props_get["playerid"]
                common["level"] = props_get["level"]
                common["vip_level"] = props_get["vip_level"]
                common["get_timestamp"] = Util.datetime_timestamp(props_get["get_tm"])
                common["get_sum"] = props_get["num"]
                common["own_after"] = props_get.get("new_num", 0)
                common["propsid"] = "_".join([k, props_get["propsid"]])
                common["get_wayid"] = props_get["get_wayid"]
                common["get_wayclassid"] = props_get.get("from_stageid", 0)
                common["get_date"] = str(props_get["get_tm"].date())
                common["get_time"] = str(props_get["get_tm"].time())
                common["type"] = props_get.get("fromid", "unbind")
                common["extend_1"] = ""
                common["extend_2"] = ""
                row_props_get = self.fill("BI_props_get|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|get_timestamp#|get_sum#|own_after#|propsid#|get_wayid#|get_wayclassid#|get_date#|get_time#|type#|extend_1#|extend_2#\n")
                self.write(row_props_get.format(**common))

    def props_consume(self, common):
        sqls = {
            "equip": "select a.playerid, a.uid, a.subid, a.equip_key as propsid, a.fromid as consume_wayid, a.log_tm, b.lv as level, b.vip as vip_level from {db_log}.log_use_equip as a inner join {db_game}.helix_player as b on a.playerid=b.playerid and log_tm>='{props_start}' and log_tm<'{start_dt}'".format(**common),
            "medal": "select a.playerid, a.uid, a.subid, a.medal_key as propsid, a.cardid as consume_wayid, a.num, a.new_num, a.log_tm, b.lv as level, b.vip as vip_level from {db_log}.log_use_medal as a inner join {db_game}.helix_player as b on a.playerid=b.playerid and log_tm>='{props_start}' and log_tm<'{start_dt}'".format(**common),
        }
        for k, sql in sqls.iteritems():
            log.info("props_consume, %s" % k)
            props_consumes = Connection.create(SERVER_LEVEL).iter(sql)
            for props_consume in props_consumes:
                common["IP"] = ""
                common["snid"] = self.get_snid(props_consume["subid"])
                common["openid"] = props_consume["uid"]
                common["roleid"] = props_consume["playerid"]
                common["level"] = props_consume["level"]
                common["vip_level"] = props_consume["vip_level"]
                common["consume_timestamp"] = Util.datetime_timestamp(props_consume["log_tm"])
                common["consume_sum"] = props_consume.get("num", 0)
                common["own_after"] = props_consume.get("new_num", 0)
                common["propsid"] = "_".join([k, props_consume["propsid"]])
                common["consume_wayid"] = props_consume["consume_wayid"]
                common["consume_wayclassid"] = -1
                common["consume_date"] = str(props_consume["log_tm"].date())
                common["consume_time"] = str(props_consume["log_tm"].time())
                common["extend_1"] = ""
                common["extend_2"] = ""
                row_props_consume = self.fill("BI_props_consume|IP#|gameid#|clientid#|snid#|openid#|roleid#|level#|vip_level#|consume_timestamp#|consume_sum#|own_after#|propsid#|consume_wayid#|consume_wayclassid#|consume_date#|consume_time#|extend_1#|extend_2#\n")
                self.write(row_props_consume.format(**common))

    def success(self):
        props_start = self.env["start"]
        self.config_set("props_start", props_start)
        self.config_save()

        props_start_dt = Util.timestamp_datetime(float(props_start))
        log.info("Props success, update props_start to %s(%s)" % (props_start, props_start_dt))


def main():
    now = int(time.time()) - 60
    try:
        run_type = sys.argv[1]

        if run_type == "b":
            extract = Extract(now)
            extract.run()
        elif run_type == "c":
            conextract = ConsumeExtract(now)
            conextract.run()
        else:
            sys.exit(2)
    except Exception as e:
        log.error("time: %s(%s) error, %s,\n%s", now, Util.timestamp_datetime(now), e, traceback.format_exc())


if __name__ == "__main__":
    main()
