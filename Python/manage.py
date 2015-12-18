# coding=utf8

import os
import sys
import inspect
import datetime
import subprocess
from functools import wraps
from contextlib import contextmanager

from bi.log import log, init as log_init
from bi import config
from bi import ddl, util


def run(cmd):
    """执行命令"""
    log.info(cmd)
    msg = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True).stdout.read()
    log.info(msg)


@contextmanager
def cd(path):
    cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


class Application(object):
    """一个部署应用对象"""
    def __init__(self):
        self.set_up()

    def set_up(self):
        _ = sys.argv[0].rsplit(os.path.sep, 1)
        if len(_) > 1:   # 当前app目录
            path = _[0]
        else:
            path = os.path.realpath(os.getcwd())
        parent = os.path.dirname(os.path.dirname(path))
        self.work_dir = parent
        self.data = os.path.join(parent, "data")
        self.clean = os.path.join(parent, "clean")
        self.history = os.path.join(parent, "history")
        self.log = os.path.join(parent, "log")
        self.shell = os.path.join(parent, "shell", "analysis")
        self.script = os.path.join(self.shell, "main.py")
        self.config = os.path.join(self.shell, "config.ini")

    def realtive_path(self, *path):
        """获得work_dir绝对目录"""
        return os.path.join(self.work_dir, *path)


class Manage(object):
    def __init__(self):
        self.cmds = {}

    def show_help(self):
        """输出支持命令列表"""
        print("support cmd:\n")
        for cmd, func in self.cmds.items():
            # 第一个参数默认是app对象
            argv = inspect.getargspec(func)[0][1:]
            print("{0}  {1}".format(cmd, tuple(argv)))

    def run(self, argv=sys.argv):
        cmd = argv[1]
        if cmd not in self.cmds:
            print("cmd: {0} not found".format(cmd))
            self.show_help()
        else:
            func = self.cmds[cmd]
            app = Application()
            return func(app, *argv[2:])

    def command(self, func):
        self.cmds[func.__name__] = func

        @wraps(func)
        def wrapper(*args, **kwargs):
            app = Application()
            return func(app, *args, **kwargs)

        return wrapper


manage = Manage()


@manage.command
def shell(app):
    """嵌入python shell"""
    def make_context():
        return dict(app=app)
    context = make_context()
    banner = ''
    # Try IPython
    try:
        try:
            # 0.10x
            from IPython.shell import IPShellEmbed
            ipshell = IPShellEmbed(banner=banner)
            ipshell(global_ns=dict(), local_ns=context)
        except ImportError:
            # 0.12+
            from IPython import embed
            embed(banner1=banner, user_ns=context)
        return
    except ImportError:
        pass
    # Use basic python shell
    import code
    code.interact(banner, local=context)


@manage.command
def clear(app, gameid=None):
    """游戏清档
    1.　删除入库表
    2.  清空histor等目录
    """
    log_init(app.realtive_path(app.log, "clear.log"))
    config.init(app.config)
    models = [ddl.AllRole, ddl.AllUser, ddl.AllAdvice, ddl.AllPayUser, ddl.PayMent, ddl.Login, ddl.Consume,
              ddl.RoleNew, ddl.RoleLogin, ddl.Levelup, ddl.Online, ddl.Mission]
    if gameid is None:
        games = util.get_gameid_from_history(app.history)
    else:
        games = [gameid]
    for game in games:
        for model in models:
            try:
                model.drop(game)
            except Exception as e:
                log.error("DDL delete error: %s", e)
    with cd(app.work_dir):
        if gameid:
            run("find clean/* -name {0}_*.csv | xargs rm".format(gameid))
            run("rm -rf history/{0}".format(gameid))
            run("rm -rf history/all_role/{0}".format(gameid))
        else:
            run("rm -rf clean/* history/*")


@manage.command
def fix(app, start, end):
    """
    假如今日13号
    python manage.py fix 2015-12-11 2015-12-12(重跑这两天的csv)
    只修复11-12号的日志
    1、清空11-12的clean
    2、删除11-12号的mysql日志
    3、修复data数据，
        11号的date里面包含了10号的数据，删除11号data中10号的数据
        12号在13号的部分数据放到12号里面
        13/0000.log -> 12/最大的日志.log
    4、ex.py cron.py
    """
    log_init(app.realtive_path(app.log, "repeat.log"))
    config.init(app.config)
    models = [ddl.AllRole, ddl.AllUser, ddl.AllAdvice, ddl.AllPayUser, ddl.PayMent, ddl.Login, ddl.Consume,
              ddl.RoleNew, ddl.RoleLogin, ddl.Levelup, ddl.Online, ddl.Mission]
    games = util.get_gameid_from_history(app.history)

    # 2删除数据库
    timestamp_day = util.timestamp(util.todate(start))
    tomorrow = util.date_delta(util.todate(end), 1)
    for game in games:
        for model in models:
            table = model.table_name(game)
            try:
                timestamp_columns = model.TIMESTAMP or filter(lambda x: x.endswith("_time"), model.FIELDS)[0]
                sql = "delete from {0} where {1} >= {2} and {1} <{3}"
                sql = sql.format(table, timestamp_columns, timestamp_day, tomorrow[1])
                model.execute(sql)
            except Exception as e:
                log.error("DDL delete error: %s", e)

    with cd(app.work_dir):

        # 处理start
        day = util.todate(start)
        directory = os.path.join(app.data, str(day))
        files = os.listdir(directory)
        fs = sorted(files)
        day_bak = os.path.join(app.data, "{0}_startbak".format(str(day)))
        if not os.path.exists(day_bak):
            os.makedirs(day_bak)
        else:
            run("rm -rf {0}/*".format(day_bak))
        for f in fs:
            run("cat {0}/{1} | grep {2} > {3}/{1}".format(directory, f, day, day_bak))
        run("mv {0} {1}/{2}_bu".format(directory, app.data, day))
        run("mv {0} {1}/{2}".format(day_bak, app.data, day))

        # 处理end
        endday = util.todate(end)
        endtomorrow = util.todate(end) + datetime.timedelta(days=1)
        enddirectory = os.path.join(app.data, str(endtomorrow))
        daydirectory = os.path.join(app.data, str(endday))
        files = os.listdir(enddirectory)
        fs = sorted(files)
        end_bak = os.path.join(app.data, "{0}_endbak".format(str(endtomorrow)))
        if not os.path.exists(end_bak):
            os.makedirs(end_bak)
        else:
            run("rm -rf {0}/*".format(end_bak))
        run("cat {0}/* | grep {1} > {2}/{3}".format(enddirectory, end, end_bak, fs[-1]))
        run("cat {0}/{2} >> {1}/{2}".format(end_bak, daydirectory, fs[-1]))

        for i in range((util.todate(end) - util.todate(start)).days + 1):
            day = util.todate(start) + datetime.timedelta(days=i)
            run("rm -rf clean/{0}".format(str(day)))
            # run("python {0}/ex.py {1}".format(app.shell,day))
            # run("python {0}/cron.py {1}".format(app.shell,day))


if __name__ == "__main__":
    manage.run()
