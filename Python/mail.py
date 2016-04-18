# coding=utf8

import os
import smtplib

from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart


class Mime(object):
    def as_string(self):
        """返回string信息"""
        return ""

    def attach(self, mime):
        """mime是MIMEMultipart
        将自身添加到mime中
        """
        pass


class Text(Mime):
    """可当html text使用"""
    def __init__(self, text):
        self.text = text

    def as_string(self):
        return self.text


class Image(Mime):
    def __init__(self, image_id, path):
        self.image_id = image_id
        self.path = path

    def as_string(self):
        return '''<img src="cid:image{0}">'''.format(self.image_id)

    def attach(self, mime):
        with open(self.path, 'rb') as fp:
            msg_image = MIMEImage(fp.read())
            msg_image.add_header("Content-ID", "<image{0}>".format(self.image_id))
            mime.attach(msg_image)


class Attachment(Mime):
    def __init__(self, path, name=None):
        self.path = path
        self.name = name

    def attach(self, mime):
        """附件名不提供则取文件名"""
        if self.name is None:
            name = os.path.basename(self.path)
        with open(self.path, 'rb') as fp:
            msg_attachment = MIMEText(fp.read())
            msg_attachment.add_header("Content-Type", "application/octet-streaapplication/octet-streamm")
            msg_attachment.add_header("Content-Disposition", "attachment; filename='{0}'".format(name))
            mime.attach(msg_attachment)


class Mail(object):
    TO_KEYS = ("To", "Cc", "Bcc")

    def __init__(self, config):
        """
        config dict:
            From  发送者(must)
            To    接受者(must)
            Cc    抄送(option)
            Bcc   密送(option)
            Smtpserver smtp服务器(must)
            Username  发送用户名(must)
            Password  发送密码(must)
            Sender 发送者(option)
        """
        self.config = config
        self.mime = MIMEMultipart("related")
        self.body = ""
        self._image_id = 1
        self._todo = []
        self.set_up()

    def check_config(self):
        """检验config配置
        To, Cc, Bcc需是序列
        """
        for key in self.TO_KEYS:
            if key in self.config:
                assert isinstance(self.config[key], (list, tuple, set))

    def set_up(self):
        self.mime["From"] = self._From
        self.mime["To"] = ";".join(self._To)
        self.mime["Subject"] = self._Subject

        # 抄送密送
        for option in self.TO_KEYS[1:]:
            if option in self.config:
                self.mime[option] = ";".join(self.config[option])

    def add_text(self, text):
        """增加文本(html)"""
        self._todo.append(Text(text))

    def add_image(self, path):
        """增加图片"""
        image = Image(self._image_id, path)
        self._image_id += 1
        self._todo.append(image)

    def add_attachment(self, path, name=None):
        """增加附件
        """
        attachment = Attachment(path, name)
        self._todo.append(attachment)

    def __getattr__(self, name):
        if name.startswith("_"):
            key = name[1:]
            return self.config[key]
        raise AttributeError(name)

    @property
    def _Sender(self):
        """邮件发送者
        mail from address must be same as authorization user
        """
        return self.config.get("Sender") or self.config["Username"]

    @property
    def _Receivers(self):
        """收件人"""
        receivers = []
        receivers.extend(self._To)
        for option in self.TO_KEYS[1:]:
            receivers.extend(self.config.get(option, []))
        return receivers

    def _prepare(self):
        """准备邮件正文"""
        for mimeobj in self._todo:
            self.body += mimeobj.as_string()

        msg_body = MIMEText(self.body, 'html', 'utf-8')
        self.mime.attach(msg_body)

        for mimeobj in self._todo:
            mimeobj.attach(self.mime)

    def send(self, report_err=True):
        self._prepare()
        try:
            smtp = smtplib.SMTP()
            smtp.connect(self._Smtpserver)
            smtp.login(self._Username, self._Password)
            smtp.sendmail(self._Sender, self._Receivers, self.mime.as_string())
            smtp.quit()
        except Exception as e:
            print(e)
            if report_err:
                raise


def test():
    config = {
        "To": ["yihaibo@longtugame.com"],
        "Cc": ["yihaibo@longtugame.com"],
        "Bcc": ["bigroup@longtugame.com"],
        'From': "bigroup@longtugame.com",
        'Subject': "测试",
        'Smtpserver': "smtp.exmail.qq.com",
        'Username': "bigroup@longtugame.com",
        'Password': "******"
    }
    mail = Mail(config)
    text = """<p><strong>ALL, 好</strong></p>"""
    mail.add_text(text)
    mail.add_image("ttt.png")
    mail.add_attachment("log.py")
    footer = '''
        <br><p>此邮件为系统自动邮件，请勿回复。</p>
        <br><br>---------------------------------
        <br>尽力为您，提供最有价值的数据、信息</strong>
        <br><br><small>如果有任何关于本邮件报表的问题，请您联系我们：
    '''
    mail.add_text(footer)
    mail.send()


if __name__ == "__main__":
    test()
