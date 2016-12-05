# coding=utf8

import os
import json
import time
import smtplib
import datetime
import operator
from collections import defaultdict

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

from statistics import util, const
from statistics import log
from basic import Perm
from statistics import models
from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError
from statistics.util import get_date_from_string


class BasicManage(object):
    def __init__(self):
        self.err = None
        self.result = {}
        self.set_up()

    def set_up(self):
        self.check_argument()

    def check_argument(self):
        pass


class Manage(BasicManage):
    """后台数据"""
    def __init__(self, request):
        self.perm = Perm(request)
        super(Manage, self).__init__()

    def game_config(self):
        """游戏gameid，区服信息"""
        # 获取game信息
        if self.perm.check:
            games = models.GameConfig.objects.filter(gameid__in=self.perm.gameids)
        else:
            games = models.GameConfig.objects.all()
        new = sorted(games, key=operator.attrgetter("id"))

        # 获取区服信息
        if self.perm.check:
            clients = models.GameClient.objects.filter(game__in=self.perm.gamepks)
        else:
            clients = models.GameClient.objects.all()
        game_clients = {c.game_id: [cid for cid in c.clientid.split('|') if cid] if c.clientid else [] for c in clients}

        cname = defaultdict(dict)
        clientsname = models.ClientName.objects.all()

        # 获取区服名称列表
        for n in clientsname:
            cname[n.gameid][n.clientid] = n.clientid_name

        # 获取平台信息
        gameid_configid = {g.gameid: g.id for g in games}
        channels = models.Channel.objects.all()
        channelid_snid = {c.id: c.snid for c in channels}
        config_channels = models.GameConfigChannel.objects.all()
        configid_channelid = defaultdict(list)
        for gc in config_channels:
            configid_channelid[gc.gameconfig_id].append(gc.channel_id)
        snids = {m.snid: m.name for m in channels}

        gameids = []
        result = {}
        allow_all_game = True
        owner_area = defaultdict(set)
        for i, game in enumerate(new):
            gameid = game.gameid
            gameids.append(gameid)
            owner_area[game.owner_id].add(game.area_id)
            all_snids = [channelid_snid[cid] for cid in configid_channelid[gameid_configid[gameid]]]
            all_snids.sort()
            game_snids = self.perm.snids.get(game.gameid)
            if game_snids:
                allow_all_game = False
            result[game.gameid] = {
                "name": self.perm.filter_name(game.name, i), "clients": game_clients.get(game.id, []),
                "client_name": cname[game.gameid],
                "snid": game_snids if game_snids else all_snids, "area": game.area_id,
                "owner": game.owner_id
            }
        self.result["allow_all_game"] = allow_all_game
        # 获取区域信息
        if self.perm.check:
            kpi = self.perm.kpi
            areas = models.Area.objects.filter(id__in=self.perm.areas.keys())
        else:
            kpi = True
            areas = models.Area.objects.all()

        self.result["areas"] = [{"id": area.id, "name": area.area} for area in areas]
        self.result["games"] = [{"id": game.id, "name": game.name, "areas": list(owner_area[game.id])}
                                for game in models.Game.objects.all() if game.id in owner_area]
        self.result["snids"] = snids
        self.result["gameids"] = gameids
        self.result["result"] = result
        self.result["kpi"] = kpi


class Action(BasicManage):
    """带action参数的请求模板，根据action分发请求，
    需定义: action_#action方法
    """
    def __init__(self, action, request):
        self.action = action
        self.request = request
        self.func = "action_{0}".format(str(action))
        super(Action, self).__init__()
        self.set_up()
        getattr(self, self.func)()

    def set_up(self):
        pass

    def get_result(self):
        """根据err错误码获取返回结果"""
        if self.err is not None:
            return util.json_failed(self.err)
        else:
            return util.json_success(self.result)

    def check_argument(self):
        if not hasattr(self, self.func):
            raise ValueError(2)

    def get_detail(self, model, pk="id"):
        """获取详细id对应的model"""
        try:
            pk = self.request.POST.get(pk)
            if pk is None or pk == "0":
                return model()
            return model.objects.get(id=int(pk))
        except (ValueError, model.DoesNotExist):
            raise ValueError(2)

    def to_bool(self, key):
        return True if self.request.POST.get(key) in ("1", "True", "true") else False

    def get_value(self, key, default=""):
        return self.request.POST.get(key, default)


class ManageUser(Action):
    """
    超级管理员不需要设置权限
    """

    def user_groups(self, users, group_detail=False):
        """根据users获取groups
        返回{uid:group}
        """
        user_groups = models.UserGroup.objects.filter(user__in=[u.id for u in users])
        if not group_detail:
            return user_groups
        gid = list(set([ug.group_id for ug in user_groups]))
        groups = {group.id: group for group in models.Group.objects.filter(id__in=gid)}
        return {ug.user_id: groups[ug.group_id] for ug in user_groups}

    def action_list(self):
        """用户列表信息(包含权限组)
        """
        users = User.objects.all()
        ug = self.user_groups(users, group_detail=True)
        self.result = [{"id": u.id, "username": u.username, "is_active": u.is_active, "name": u.first_name,
                        "groupname": "管理员" if u.is_superuser else ug[u.id].name if u.id in ug else "无权限组"} for u in users]

    def action_load(self):
        """用户详细信息
        """
        user = self.get_detail(User)
        self.result = {
            "id": user.id,
            "name": user.first_name,
            "username": user.username,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
        }
        if not user.is_superuser:
            ug = self.user_groups([user])
            if len(ug)>0:
                self.result["group_id"] = ug[0].group_id

    def action_update(self):
        """用户更新和新建"""
        user = self.get_detail(User)
        user.is_superuser = self.to_bool("is_superuser")
        user.username = self.get_value("username")
        user.first_name = self.get_value("name")
        user.is_active = self.to_bool("is_active")
        user.is_staff = True
        if self.get_value("password"):
            user.set_password(self.get_value("password"))
        if self.get_value("newpassword"):
            user.set_password(self.get_value("newpassword"))
        user.save()

        group_id = self.get_value("group_id")
        ugs = self.user_groups([user])
        # 之前有权限组
        if len(ugs) > 0:
            ug = ugs[0]
            if group_id:   # 有group_id更新
                group_id = int(group_id)
                if ug.group_id != group_id:
                    ug.group_id = group_id
                    ug.save()
            else:
                ug.delete()
        else:
            if group_id:
                ug = models.UserGroup(user_id=user.id, group_id=int(group_id))
                ug.save()

    def action_delete(self):
        """用户删除"""
        user = self.get_detail(User)
        user.delete()
        if not user.is_superuser:
            ug = self.user_groups([user])
            if len(ug) > 0:
                ug[0].delete()

    def action_unbind(self):
        from login import Login
        user = self.get_detail(User)
        login = Login(user)
        login.unbind_weixin()


class ManageGroup(Action):
    def action_list(self):
        """获取分组简洁信息"""
        groups = models.Group.all_group(staff=True, desc=True)

        self.result = [{"id": g.id, "name": g.name, "is_active": g.is_staff} for g in groups]

    def action_load(self):
        """组详细信息"""
        g = self.get_detail(models.Group)
        self.result = {
            "id": g.id,
            "name": g.name,
            "is_active": g.is_staff,
            "is_super": g.is_super,
            "comment": g.comment,
            "games": g.games,
            "snids": json.loads(g.snids) if g.snids else None,
            "kpi": g.kpi,
            "menu": g.menu.split("|")
        }

    def action_update(self):
        """组更新和新建"""
        group = self.get_detail(models.Group)
        group.name = self.get_value("name")
        group.is_staff = self.to_bool("is_active")
        group.is_super = self.to_bool("is_super")
        group.comment = self.get_value("comment")
        group.games = self.get_value("games")
        group.snids = self.get_value("snids")
        group.kpi = self.to_bool("kpi")
        group.menu = self.get_value("menu")
        group.save()

    def action_delete(self):
        """组删除"""
        group = self.get_detail(models.Group)
        group.delete()


class ManageMonitor(Action):
    def action_type(self):
        """获取监控类别"""
        self.result = [{"id": 1, "name": "补数据"}]

    def action_list(self):
        """获取具体监控类别"""
        start = get_date_from_string(self.get_value("start"))
        end = get_date_from_string(self.get_value("end"))
        classify = self.get_value("type")

        def parse_1(log):
            """解析classify为1"""
            msg = json.loads(log.msg)
            row = "table:{table}, max:{d_max}, min:{d_min}".format(**msg)

            return {"msg": row}

        logs = models.Log.objects.filter(ds__range=[start, end], type=classify)

        name = "parse_{0}".format(classify)

        if name not in locals():
            return
        res = []
        func = locals()[name]

        for log in logs:
            row = {"ds": log.ds, "gameid": log.gameid}
            row.update(func(log))
            res.append(row)

        self.result = res


class ManageDevice(Action):
    """设备管理"""
    def action_list(self):
        """设备列表"""
        devices = models.Device.objects.all()
        self.result = [{"id": g.id, "outer": g.outer, "inner": g.inner, "hardware": g.hardware, "application": g.application, "classification": g.classification} for g in devices]

    def action_load(self):
        """设备详细信息"""
        device = self.get_detail(models.Device)
        if device.classification == 1:
            # 上报服务器
            apps_result = []
            try:
                attr = device.analysedevice_set.all()[:1][0]
            except IndexError:
                attr = None
            else:
                apps = attr.analyseapplication_set.all()
                apps_result = [{"id": app.id, "game": app.game, "directory": app.directory, "share": app.share,
                                "shell": app.shell, "history": app.history, "node": app.node, "version": app.version,
                                "multi_role": app.multi_role, "standalone": app.standalone, "store": app.store, "rsync_name": app.rsync_name,
                                "rsync_path": app.rsync_path, "snapshot_path": app.snapshot_path,
                                "consume_path": app.consume_path, "games": app.games
                               } for app in apps]
            common = {
                "id": device.id,
                "outer": device.outer,
                "inner": device.inner,
                "hardware": device.hardware,
                "application": device.application,
                "classification": device.classification,
                "shell": attr.shell if attr is not None else ""
            }
            self.result = {"common": common, "app": apps_result}
        else:
            common = {
                "id": device.id,
                "outer": device.outer,
                "inner": device.inner,
                "hardware": device.hardware,
                "application": device.application,
                "classification": device.classification
            }
            self.result = {"common": common}

    def action_update_device(self):
        """ 设备与分析服务器配置更新与新建"""
        device = self.get_detail(models.Device)
        device.outer = self.get_value("outer")
        device.inner = self.get_value("inner")
        device.hardware = self.get_value("hardware")
        device.application = self.get_value("application")
        device.classification = self.get_value("classification")
        try:
            if self.get_value("classification") == "1":
                device.save()
                attr_exist = models.AnalyseDevice.objects.filter(equipment=device.id)
                if not attr_exist:
                    models.AnalyseDevice.objects.create(equipment_id=device.id, shell=self.get_value("shell"))
                else:
                    attr = models.AnalyseDevice.objects.get(equipment=device.id)
                    attr.shell = self.get_value("shell")
                    attr.save()
            else:
                device.save()
        except IntegrityError:
            raise ValueError(16)

    def action_update_apps(self):
        """ 分析应用配置更新与新建"""

        def update_app(app):
            app.game = self.get_value("game")
            app.node = self.get_value("node")
            app.version = self.get_value("version")
            app.multi_role = self.to_bool("multi_role")
            app.standalone = self.to_bool("standalone")
            app.directory = self.get_value("directory")
            app.share = self.to_bool("share")
            app.shell = self.get_value("shell")
            app.history = self.get_value("history")
            app.store = self.get_value("store")
            app.rsync_name = self.get_value("rsync_name")
            app.rsync_path = self.get_value("rsync_path")
            app.snapshot_path = self.get_value("snapshot_path", app.rsync_path)
            app.consume_path = self.get_value("consume_path", app.rsync_path)
            app.save()

        if self.get_value("device_id"):   # new
            app = self.get_detail(models.AnalyseApplication)
            device = models.AnalyseDevice.objects.get(equipment=self.get_value("device_id"))
            app.device_id = device.id
            update_app(app)
            self.result = {"id": app.id}
        else:   # update
            app = self.get_detail(models.AnalyseApplication)
            update_app(app)

    def action_update_delete(self):
        apps = self.get_detail(models.AnalyseApplication)
        apps.delete()

    def fab_auto(self, name, *args):
        try:
            msg = util.fab_call(name, *args)
        except Exception as e:
            msg = str(e)

        self.result = {"msg": msg}

    def action_deploy(self):
        """部署"""
        app_id = self.get_value("id")
        self.fab_auto("deploy_app", app_id)

    def action_deploy_snapshot(self):
        """部署快照"""
        app_id = self.get_value("id")
        self.fab_auto("deploy_snapshot", app_id)

    def action_deploy_consume(self):
        """部署消耗"""
        app_id = self.get_value("id")
        self.fab_auto("deploy_consume", app_id)

    def action_clear(self):
        """清党操作"""
        app_id = self.get_value("id")
        self.fab_auto("clear_app", app_id)


class Mail(object):
    def get_kv_by_key(self):
        try:
            return models.Kv.objects.get(key=self.key)
        except models.Kv.DoesNotExist:
            return None

    def get_detail(self):
        obj = self.get_kv_by_key()
        if obj is not None:
            return json.loads(obj.value)
        else:
            return self.default_detail()

    def set_detail(self, detail):
        obj = self.get_kv_by_key()
        if obj is None:
            obj = models.Kv(key=self.key, value=json.dumps(detail))
        else:
            obj.value = json.dumps(detail)

        obj.save()


class SmtpMail(Mail):
    key = "smtp_key"

    def smtp_detail(self, server, port):
        return {"server": server, "port": port}

    def default_detail(self):
        return self.smtp_detail(None, 25)


class SmtpSender(Mail):
    key = "mail_sender"

    def sender_detail(self, sender, password, subject, games, receipt, testreceipt, secretcc):
        res = {}
        res["sender"] = sender
        res["password"] = password
        res["subject"] = subject
        res["games"] = games.split(',') if games else []
        res["receipt"] = receipt.split(',') if receipt else []
        res["testreceipt"] = testreceipt.split(',') if testreceipt else []
        res["secretcc"] = secretcc.split(',') if secretcc else []
        return res

    def default_detail(self):
        return self.sender_detail("bigroup@longtugame.com", None, None, None, None, None, None)


class InternalSender(SmtpSender):
    key = "internal_mail_sender"


class OuterSender(SmtpSender):
    key = "outer_mail_sender"


class AllInternalSender(SmtpSender):
    key = "all_internal_mail_sender"


class AllOuterSender(SmtpSender):
    key = "all_outer_mail_sender"


class ManageMail(Action):
    """邮件发送"""
    MAPS = {
        "kpi": SmtpSender,
        "internal": InternalSender,
        "outer": OuterSender,
        "all_internal": AllInternalSender,
        "all_outer": AllOuterSender,
        "all": AllInternalSender,
    }

    def __init__(self, action, request, classify=None):
        # self.image_dir = '/data/biweb/email_data/'
        self.image_dir = os.path.join(settings.BASE_DIR, '..', 'email_data')
        self.classify = classify
        super(ManageMail, self).__init__(action, request)

    def set_up(self):
        if self.classify is None:
            self.classify = self.get_value("classify")

    def image_name(self, suffix):
        return ''.join([str(datetime.date.today()), "_", suffix, '.png'])

    def image_path(self, suffix):
        return os.path.join(self.image_dir, self.image_name(suffix))

    def action_list(self):
        base = "".join(["http://", self.request.META["HTTP_HOST"], "/email/data/"])
        mail_config = {}
        smtp = SmtpMail().get_detail()
        for key, cls in self.MAPS.iteritems():
            sender = cls().get_detail()
            mail_config.update(smtp)
            mail_config.update(sender)
            mail_config['receipt'] = ','.join(sender['receipt'])
            mail_config['testreceipt'] = ','.join(sender['testreceipt'])
            mail_config['secretcc'] = ','.join(sender['secretcc'])
            self.result[key] = {"data_url": base + self.image_name(key)}
            self.result[key].update(mail_config)

    def action_update(self):
        sm = SmtpMail()
        cls = self.MAPS.get(self.classify)
        if cls is None:
            raise ValueError(2)
        ss = cls()
        server = self.get_value("server")
        port =self.get_value("port")
        sender = self.get_value("sender")
        password = self.get_value("password")
        subject =self.get_value("subject")
        games = self.get_value("games")
        receipt = self.get_value("receipt")
        testreceipt = self.get_value("testreceipt")
        secretcc = self.get_value("secretcc")
        sm.set_detail(sm.smtp_detail(server, port))
        ss.set_detail(ss.sender_detail(sender, password, subject, games, receipt, testreceipt, secretcc))

    def action_sendmail(self, is_test=False):
        self.mail_config = {}
        smtp = SmtpMail().get_detail()
        cls = self.MAPS.get(self.classify)
        if cls is None:
            raise ValueError(2)
        sender = cls().get_detail()
        self.mail_config.update(smtp)
        self.mail_config.update(sender)

        username = self.mail_config['sender']
        password = self.mail_config['password']
        sender = self.mail_config['sender']
        receiver = self.mail_config['receipt']
        cc = self.mail_config['secretcc']
        test_receiver = self.mail_config['testreceipt']
        subject = self.mail_config['subject']
        smtpserver = self.mail_config['server']

        msg = MIMEMultipart('related')
        msg['From'] = sender
        msg['To'] = ';'.join(receiver)
        msg['Cc'] = ';'.join(cc)

        common_text = '''
            <br><p>此邮件为系统自动邮件，请勿回复。</p>
            <br><br>---------------------------------
            <br><p><strong>龙图游戏BI -- 邮件日报
            <br>尽力为您，提供最有价值的数据、信息</strong>
            <br><br><small>如果有任何关于本邮件报表的问题，请您联系我们：
            <br>龙图游戏BI，bi@longtugame.com</small></p>
        '''

        if is_test:
            if self.request:
                url = 'http://%s/daily_data/' % (self.request.META.get('HTTP_HOST', const.DOMAIN))
            else:
                url = 'http://%s/daily_data/' % (const.DOMAIN)
            url += '%s/?action=confirm&sign=4923fa2c5ae1acc03a1d25a5f221d4d6' % self.classify
            text = '''
                <p><strong>ALL, 好</strong></p>
                <img src="cid:image1">
                <img src="cid:image2">
                <br><p>请点击链接去确认： <a target="_blank" href="%s">%s</a></p>
                %s
                ''' % (url, url, common_text)
            receivers = test_receiver
            msg['Subject'] = subject + u'（测试）' + ''.join([u'（', str(datetime.date.today()), u'）'])
        else:
            if self.classify == 'internal' or self.classify == 'all_internal':
                text = '''
                    <p><strong>ALL, 好</strong></p>
                    <img src="cid:image1">
                    <img src="cid:image2">
                    %s
                    ''' % (common_text)
            else:
                text = '''
                    <p><strong>ALL, 好</strong></p>
                    <img src="cid:image1">
                    %s
                    ''' % (common_text)
            receivers = receiver + cc
            msg['Subject'] = subject + ''.join([u'（', str(datetime.date.today()), u'）'])
        msg_text = MIMEText(text, 'html', 'utf-8')
        msg.attach(msg_text)

        with open(self.image_path(self.classify), 'rb') as fp:
            msg_image = MIMEImage(fp.read())
        msg_image.add_header('Content-ID', '<image1>')
        msg.attach(msg_image)

        if self.classify == 'internal':
            with open(self.image_path('outer'), 'rb') as fp:
                msg_image2 = MIMEImage(fp.read())
            msg_image2.add_header('Content-ID', '<image2>')
            msg.attach(msg_image2)

        if self.classify == 'all_internal':
            with open(self.image_path('all_outer'), 'rb') as fp:
                msg_image2 = MIMEImage(fp.read())
            msg_image2.add_header('Content-ID', '<image2>')
            msg.attach(msg_image2)

        try:
            smtp = smtplib.SMTP()
            smtp.connect(smtpserver)
            smtp.login(username, password)
            smtp.sendmail(sender, receivers, msg.as_string())
            smtp.quit()
        except Exception, e:
            log.trace_exception(e, classify=self.classify)
            print e

    def action_redraw(self):
        if self.request:
            url = 'http://%s/daily_data/' % (self.request.META.get('HTTP_HOST', const.DOMAIN))
        else:
            url = 'http://%s/daily_data/' % (const.DOMAIN)
        url += '%s/?sign=4923fa2c5ae1acc03a1d25a5f221d4d6' % self.classify

        display = Display(visible=0, size=(1024, 768))
        display.start()

        browser = webdriver.Firefox()
        browser.set_window_size(1024, 768)
        browser.get(url)

        try:
            wait = WebDriverWait(browser, 60)
            wait.until(EC.presence_of_element_located((By.ID, 'complete')))
        except Exception, e:
            log.trace_exception(e, classify=self.classify)
            print e

        browser.execute_script('''
            (function () {
                var y = 0;
                var step = 100;
                window.scroll(0, 0);

                function f() {
                    if (y < document.body.scrollHeight) {
                        y += step;
                        window.scroll(0, y);
                        setTimeout(f, 50);
                    } else {
                        window.scroll(0, 0);
                        document.title += "scroll-done";
                    }
                }

                setTimeout(f, 1000);
            })();
        ''')

        for i in xrange(30):
            if 'scroll-done' in browser.title:
                break
            time.sleep(1)

        browser.save_screenshot(self.image_path(self.classify))
        browser.close()
        browser.quit()
        display.stop()

    def action_cronmail(self):
        self.action_redraw()
        if self.classify != 'outer' or self.classify != 'all_outer':
            self.action_sendmail(is_test=False)
